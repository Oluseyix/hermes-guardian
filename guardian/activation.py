"""Operator-only activation through the public atomic ctx.set_config API."""
import copy
import fcntl
import json
import os
from pathlib import Path
import stat
from uuid import uuid4
from .builder import check_proposal, digest
from .policy import DEFAULT


class ActivationError(RuntimeError):
    """Payload-free operator recovery error."""


def _sync_file(directory_fd, name, payload):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
    try:
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def activate(ctx, value, *, confirmation, storage):
    """Requires reviewed digest, backup, unchanged baseline and no pending questions.

    Only a terminal operator calls this; never exposed as an agent tool. The
    host owns atomic config merge/replace. Cooperating Guardian writers lock;
    other config editors must be stopped during activation.
    """
    previous = copy.deepcopy(ctx.get_config('policy', DEFAULT))
    checked = check_proposal(value, previous)
    if checked['questions']:
        raise ValueError('Resolve clarification questions before activation.')
    if confirmation != 'ACTIVATE ' + digest(checked):
        raise ValueError('Explicit confirmation of this exact proposal is required.')
    directory = Path(storage())
    dir_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    lock_fd = None
    try:
        if os.fstat(dir_fd).st_uid != os.getuid():
            raise ValueError('Activation storage must be owned by this user.')
        lock_fd = os.open('activation.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=dir_fd)
        info = os.fstat(lock_fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600:
            raise ValueError('Unsafe activation lock.')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if ctx.get_config('policy', DEFAULT) != previous:
            raise ValueError('Policy changed during review; regenerate.')
        identifier = uuid4().hex
        temporary, backup = '.policy-' + identifier + '.tmp', 'policy-backup-' + identifier + '.json'
        payload = (json.dumps({'schema': 1, 'policy': previous}, sort_keys=True, indent=2) + '\n').encode()
        _sync_file(dir_fd, temporary, payload)
        os.rename(temporary, backup, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
        os.fsync(dir_fd)
        try:
            ctx.set_config('policy', checked['policy'])
            if ctx.get_config('policy', DEFAULT) != checked['policy']:
                raise RuntimeError('Host readback did not match proposed policy.')
        except Exception:
            # An atomic host writer may report an error after replacement. Restore
            # the previous effective policy, rather than assuming no write occurred.
            try:
                if ctx.get_config('policy', DEFAULT) != previous:
                    ctx.set_config('policy', previous)
                if ctx.get_config('policy', DEFAULT) != previous:
                    raise RuntimeError('Rollback readback failed.')
            except Exception:
                raise ActivationError('Activation and rollback failed. Stop the agent; recover from the policy backup in plugin storage.') from None
            raise ActivationError('Activation failed; previous policy preserved. Backup retained.') from None
        return {'activated': True, 'proposal_digest': digest(checked), 'backup': str(directory / backup)}
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        os.close(dir_fd)
