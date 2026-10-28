#!/usr/bin/env python3
"""Run one bounded GPU experiment and restore the exact retrieval service set.

The public CLI launches a transient user service. Only its supervisor touches
services, under the shared GPU lock; ExecStopPost provides independent recovery.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid


MANAGED = ('rag-embed.service', 'rag-rerank.service', 'local-reasoner.service')
HEALTH = {'rag-embed.service': 'http://127.0.0.1:8001/health',
          'rag-rerank.service': 'http://127.0.0.1:8002/health',
          'local-reasoner.service': 'http://127.0.0.1:8000/health'}
CACHE = Path.home() / '.cache/3d-lab'
LOCK = CACHE / 'gpu.lock'
LEASE = CACHE / 'surface-lifting-gpu-lease.json'
SCRIPT = Path(__file__).resolve()
RESTORE_HEALTH_TIMEOUT = 180
RESTORE_POLICY = 'sequential-http-ready-v1'


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temp.write_text(json.dumps(data, indent=2) + '\n')
    temp.replace(path)


def load_json(path):
    return json.loads(Path(path).read_text())


def ctl(*arguments, check=True):
    return subprocess.run(['systemctl', '--user', *arguments], check=check,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                          timeout=100)


def unit_state(unit):
    if unit not in MANAGED:
        raise RuntimeError('Service outside experiment allowlist')
    result = ctl('show', unit, '-p', 'LoadState', '-p', 'ActiveState', '-p', 'SubState')
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


def snapshot():
    result = {}
    for unit in MANAGED:
        state = unit_state(unit)
        if state.get('LoadState') != 'loaded' or (state.get('ActiveState'), state.get('SubState')) not in {
                ('active', 'running'), ('inactive', 'dead')}:
            raise RuntimeError(f'{unit} has an unsupported/transitional state: {state}')
        result[unit] = state
    return result


def gpu_stats():
    result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.free,temperature.gpu',
                             '--format=csv,noheader,nounits'], check=True,
                            capture_output=True, text=True, timeout=10)
    lines = result.stdout.strip().splitlines()
    if len(lines) != 1:
        raise RuntimeError('This guard requires exactly one NVIDIA GPU')
    used, free, temperature = [int(x.strip()) for x in lines[0].split(',')]
    return {'used_mib': used, 'free_mib': free, 'temperature_c': temperature}


def managed_allocations():
    """Attribute numeric GPU memory to allowlisted cgroups, never command lines."""
    result = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,used_gpu_memory',
                             '--format=csv,noheader,nounits'], check=True,
                            capture_output=True, text=True, timeout=10)
    memory = {unit: 0 for unit in MANAGED}
    for line in result.stdout.splitlines():
        fields = [part.strip() for part in line.split(',')]
        if len(fields) != 2 or not all(value.isdigit() for value in fields):
            continue
        try:
            cgroup = Path('/proc') / fields[0] / 'cgroup'
            components = cgroup.read_text().strip().split('/')
        except FileNotFoundError:
            continue
        for unit in MANAGED:
            if unit in components:
                memory[unit] += int(fields[1])
    return memory


def available_ram_mib():
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):
            return int(line.split()[1]) // 1024
    raise RuntimeError('Cannot read host memory reserve')


def acquire_lock():
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    handle = LOCK.open('a+')
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        handle.close()
        raise RuntimeError('Another 3D job owns the shared GPU lock')
    return handle


def assert_no_unfinished_lease():
    if LEASE.exists():
        lease = load_json(LEASE)
        if lease.get('phase') != 'restored':
            raise RuntimeError('Unfinished GPU lifecycle lease; recover its state before starting another job')


def same_lease(state):
    if not LEASE.exists():
        return False
    lease = load_json(LEASE)
    return lease.get('job_id') == state['job_id'] and lease.get('state_path') == state['state_path']


def save_state(state, phase=None):
    if phase:
        state['phase'] = phase
    atomic_json(state['state_path'], state)


def stop_worker(proc):
    if proc is None:
        return
    # Even if the leader already exited, terminate any surviving group members.
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        proc.wait()
        return
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        proc.poll()
        try:
            os.killpg(proc.pid, 0)
        except ProcessLookupError:
            proc.wait()
            return
        time.sleep(.1)
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


def health_check(unit, seconds=RESTORE_HEALTH_TIMEOUT):
    deadline = time.monotonic() + seconds
    while True:
        try:
            before = unit_state(unit)
            if (before.get('ActiveState'), before.get('SubState')) == ('active', 'running'):
                with urllib.request.urlopen(HEALTH[unit], timeout=1) as response:
                    after = unit_state(unit)
                    if response.status == 200 and (after.get('ActiveState'), after.get('SubState')) == ('active', 'running'):
                        return True
        except (OSError, urllib.error.URLError, subprocess.SubprocessError):
            pass
        if time.monotonic() >= deadline:
            return False
        time.sleep(.5)


def restore_state(state_path, lock_held=False):
    """Idempotent normal and ExecStopPost cleanup; unfinished leases stay blocking."""
    handle = None
    if not lock_held:
        handle = acquire_lock()
    try:
        state = load_json(state_path)
        if state.get('phase') == 'restored':
            # Older guard versions marked active-but-unready services restored.
            # Revalidate those records when they still own the lifecycle lease;
            # never reopen a historical state while another job owns the lease.
            if not same_lease(state):
                return True
            verified = state.get('restoration_policy') == RESTORE_POLICY and all(
                state.get('restoration', {}).get(unit, {}).get('active') is True
                and state.get('restoration', {}).get(unit, {}).get('http_ready') is True
                for unit in state.get('active_before', []))
            if verified:
                atomic_json(LEASE, {'job_id': state['job_id'], 'state_path': state['state_path'], 'phase': 'restored'})
                return True
            atomic_json(LEASE, {'job_id': state['job_id'], 'state_path': state['state_path'], 'phase': 'unfinished'})
        if not state.get('lease_committed'):
            return True  # Launcher/snapshot failed before service mutation was allowed.
        if not same_lease(state):
            raise RuntimeError('Recovery lease identity does not match; refusing service changes')
        wanted = state.get('active_before', [])
        if any(unit not in MANAGED for unit in wanted):
            raise RuntimeError('Recovery state contains a non-allowlisted service')
        if state.get('worker_pid') and not state.get('worker_reaped'):
            state['worker_status'] = 'interrupted'
            state['worker_cleanup_backend'] = 'systemd-control-group-before-ExecStopPost'
        save_state(state, 'restoring')
        # Normal cleanup has reaped the process group. ExecStopPost runs only after
        # systemd has stopped the service cgroup, covering supervisor SIGKILL/OOM.
        results = state.setdefault('restoration', {})
        state['restoration_policy'] = RESTORE_POLICY
        state['restoration_health_timeout_seconds'] = RESTORE_HEALTH_TIMEOUT
        state['restoration_pending'] = []
        success = True
        for unit_index, unit in enumerate(wanted):
            try:
                # A partial stop or previous restoration attempt can leave other
                # retrieval units running. Require headroom for this unit only.
                current = unit_state(unit).get('ActiveState')
                if current != 'active':
                    needed = state.get('managed_gpu_mib', {}).get(unit, 0)
                    deadline = time.monotonic() + 20
                    while True:
                        stats = gpu_stats()
                        if stats['free_mib'] >= needed + state['settings']['reserve_mib']:
                            break
                        if time.monotonic() >= deadline:
                            raise RuntimeError(f'Insufficient VRAM to restore {unit}; recovery lease retained')
                        time.sleep(1)
                    state['restore_gpu_preflight'] = stats
                    ctl('start', unit)
                ready = health_check(unit, seconds=RESTORE_HEALTH_TIMEOUT)
                observed = unit_state(unit)
                active = (observed.get('ActiveState'), observed.get('SubState')) == ('active', 'running')
                results[unit] = {'active': active, 'http_ready': ready,
                                 'observed_state': observed}
                if not (active and ready):
                    results[unit]['error'] = 'Service did not become active and HTTP ready within the restoration deadline'
                    success = False
                else:
                    results[unit]['gpu_after_ready'] = gpu_stats()
            except Exception as exc:
                results[unit] = {'active': False, 'error': str(exc)}
                success = False
            save_state(state)
            if not success:
                # Do not overlap another model startup with an unready/restarting
                # unit. ExecStopPost or an explicit recovery may retry later.
                state['restoration_pending'] = wanted[unit_index + 1:]
                break
        # Originally inactive services must still be inactive. Do not stop units
        # started externally; retain the lease and report the conflict instead.
        for unit in MANAGED:
            if unit not in wanted and unit_state(unit).get('ActiveState') != 'inactive':
                success = False
                state.setdefault('restoration_conflicts', []).append(unit)
        state['restoration_succeeded'] = success
        save_state(state, 'restored' if success else 'restore_failed')
        if success:
            atomic_json(LEASE, {'job_id': state['job_id'], 'state_path': state['state_path'], 'phase': 'restored'})
        return success
    finally:
        if handle is not None:
            handle.close()


def supervise(state_path):
    state = load_json(state_path)
    lock = acquire_lock()
    proc = None
    handlers = {}
    rc = 1
    def interrupted(signum, frame):
        raise KeyboardInterrupt(f'Experiment interrupted by signal {signum}')
    try:
        assert_no_unfinished_lease()
        for sig in (signal.SIGTERM, signal.SIGINT):
            handlers[sig] = signal.signal(sig, interrupted)
        state['snapshot'] = snapshot()
        state['active_before'] = [unit for unit, info in state['snapshot'].items() if info['ActiveState'] == 'active']
        state['gpu_before'] = gpu_stats()
        state['managed_gpu_mib'] = managed_allocations()
        state['ram_available_before_mib'] = available_ram_mib()
        # State first, lease second; no stop is allowed until both writes succeed.
        state['lease_committed'] = True
        save_state(state, 'snapshot_saved')
        atomic_json(LEASE, {'job_id': state['job_id'], 'state_path': state['state_path'], 'phase': 'unfinished'})
        state['stopped_units'] = []
        for unit in state['active_before']:
            ctl('stop', unit)
            if unit_state(unit).get('ActiveState') != 'inactive':
                raise RuntimeError(f'{unit} did not stop')
            state['stopped_units'].append(unit)
            save_state(state, 'stopping')
        deadline = time.monotonic() + 90
        while gpu_stats()['free_mib'] < state['settings']['min_free_mib']:
            if time.monotonic() >= deadline:
                raise RuntimeError('GPU did not reach required initial headroom')
            time.sleep(1)
        if available_ram_mib() < state['settings']['ram_reserve_mib']:
            raise RuntimeError('Host RAM reserve is insufficient before worker start')
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env.setdefault('OMP_NUM_THREADS', '4')
        env.setdefault('OPENBLAS_NUM_THREADS', '4')
        env.setdefault('PYTORCH_CUDA_ALLOC_CONF', 'expandable_segments:True')
        started = time.monotonic()
        with Path(state['worker_log']).open('w') as log:
            proc = subprocess.Popen(state['command'], stdout=log, stderr=subprocess.STDOUT,
                                    env=env, start_new_session=True)
            state['worker_pid'] = proc.pid
            save_state(state, 'running')
            while proc.poll() is None:
                stats = gpu_stats()
                ram = available_ram_mib()
                state['last_gpu'] = stats
                state['min_free_vram_mib'] = min(stats['free_mib'], state.get('min_free_vram_mib', stats['free_mib']))
                state['min_available_ram_mib'] = min(ram, state.get('min_available_ram_mib', ram))
                if stats['free_mib'] < state['settings']['reserve_mib']:
                    raise RuntimeError('GPU free-memory reserve crossed')
                if stats['temperature_c'] >= 90:
                    raise RuntimeError('GPU reached 90 C thermal guard')
                if ram < state['settings']['ram_reserve_mib']:
                    raise RuntimeError('Host RAM reserve crossed')
                if time.monotonic() - started > state['settings']['timeout']:
                    raise RuntimeError('Experiment worker timed out')
                save_state(state)
                time.sleep(.5)
            rc = proc.returncode
            state['worker_exit_code'] = rc
            state['worker_status'] = 'completed' if rc == 0 else 'failed'
    except (Exception, KeyboardInterrupt) as exc:
        state['worker_status'] = 'failed'
        state['error'] = str(exc)
        rc = 130 if isinstance(exc, KeyboardInterrupt) else 1
    finally:
        for sig in handlers:
            signal.signal(sig, signal.SIG_IGN)
        try:
            stop_worker(proc)
            state['worker_reaped'] = True
            save_state(state)
            if state.get('lease_committed') and same_lease(state):
                if not restore_state(state_path, lock_held=True):
                    rc = 1
        except Exception as exc:
            state = load_json(state_path)
            state['cleanup_error'] = str(exc)
            save_state(state)
            rc = 1
        finally:
            lock.close()
            for sig, handler in handlers.items():
                signal.signal(sig, handler)
    return rc


def launch(args):
    output = args.out.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    state_path = output / 'gpu_runtime.json'
    if state_path.exists() or (output / 'gpu_worker.log').exists():
        raise RuntimeError('GPU runtime outputs already exist; choose a fresh run directory')
    # This check is advisory; the authoritative lease check happens under flock.
    assert_no_unfinished_lease()
    identity = uuid.uuid4().hex
    unit = 'surface-lifting-gpu-' + identity + '.service'
    state = {'job_id': identity, 'unit': unit, 'state_path': str(state_path),
             'phase': 'planned', 'command': args.command,
             'worker_log': str(output / 'gpu_worker.log'),
             'settings': {'min_free_mib': args.min_free_mib, 'reserve_mib': args.reserve_mib,
                          'timeout': args.timeout, 'ram_reserve_mib': 8192,
                          'host_memory_gib': args.host_memory_gib}}
    atomic_json(state_path, state)
    # systemd parses ExecStopPost as a command line; quote path arguments with
    # its own quoting rules and escape percent specifiers. No shell is involved.
    def quote(value):
        return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%') + '"'
    recovery = ' '.join(quote(x) for x in [sys.executable, SCRIPT, '--restore', state_path])
    command = ['systemd-run', '--user', '--wait', '--pipe', '--collect', '--quiet', '--unit=' + unit,
               '-p', 'Type=exec', '-p', 'KillMode=control-group', '-p', f'MemoryMax={args.host_memory_gib}G',
               '-p', 'MemorySwapMax=0', '-p', 'OOMPolicy=stop',
               '-p', 'RuntimeMaxSec=' + str(args.timeout + 900), '-p', 'TimeoutStopSec=900',
               '-p', 'ExecStopPost=' + recovery,
               str(sys.executable), str(SCRIPT), '--supervise', str(state_path)]
    print(f'GPU experiment unit: {unit}\nLifecycle metadata: {state_path}', flush=True)
    try:
        return subprocess.run(command, check=False).returncode
    except KeyboardInterrupt:
        ctl('stop', unit, check=False)
        return 130


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    internal = parser.add_mutually_exclusive_group()
    internal.add_argument('--restore', type=Path)
    internal.add_argument('--supervise', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--min-free-mib', type=int, default=16000)
    parser.add_argument('--reserve-mib', type=int, default=3000)
    parser.add_argument('--timeout', type=float, default=900)
    parser.add_argument('--host-memory-gib', type=int, default=12,
                        help='Worker cgroup RAM ceiling; full TRELLIS generation needs more than codec-only jobs')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        if args.restore:
            return 0 if restore_state(args.restore.resolve()) else 1
        if args.supervise:
            return supervise(args.supervise.resolve())
        if args.command[:1] == ['--']:
            args.command = args.command[1:]
        if not args.out or not args.command:
            parser.error('--out and a worker command after -- are required')
        if not 0 < args.reserve_mib < args.min_free_mib or args.timeout <= 0 or not 1 <= args.host_memory_gib <= 48:
            parser.error('Require 0 < reserve < minimum free memory, a positive timeout, and 1..48 GiB host RAM')
        return launch(args)
    except Exception as exc:
        print(f'GPU runtime: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
