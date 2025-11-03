from subpar_async.scheduler import sched

def foo():
    while True:
        print("foo")
        yield from sched.sleep(1)

def bar():
    while True:
        print("bar")
        yield from sched.sleep(3)


sched.add_task(foo())
sched.add_task(bar())
sched.run()