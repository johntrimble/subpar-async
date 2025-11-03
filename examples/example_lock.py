from subpar_async.scheduler import sched, AsyncLock

def named_task(name: str, lock: AsyncLock):
    yield from lock.acquire()
    try:
        print(f"{name} acquired lock")
        yield from sched.sleep(4)
    finally:
        lock.release()

lock = AsyncLock()

for i in range(20):
    sched.add_task(named_task(f"task-{i}", lock))

# Should see tasks run in groups of 2
sched.run()
