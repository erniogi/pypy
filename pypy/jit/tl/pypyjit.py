"""
A temporary file that invokes translation of PyPy with the JIT enabled.
"""

import py, os

from pypy.objspace.std import Space
from pypy.config.translationoption import set_opt_level
from pypy.config.pypyoption import get_pypy_config, set_pypy_opt_level

config = get_pypy_config(translating=True)
config.translation.backendopt.inline_threshold = 0
set_opt_level(config, level='1')
config.objspace.compiler = 'ast'
config.objspace.nofaking = True
config.objspace.allworkingmodules = False
config.objspace.usemodules.pypyjit = True
set_pypy_opt_level(config, level='0')
print config

space = Space(config)
w_dict = space.newdict()


def readfile(filename):
    fd = os.open(filename, os.O_RDONLY, 0)
    blocks = []
    while True:
        data = os.read(fd, 4096)
        if not data:
            break
        blocks.append(data)
    os.close(fd)
    return ''.join(blocks)

def entry_point():
    source = readfile('pypyjit_demo.py')
    ec = space.getexecutioncontext()
    code = ec.compiler.compile(source, '?', 'exec', 0)
    code.exec_code(space, w_dict, w_dict)


def test_run_translation():
    from pypy.translator.goal.ann_override import PyPyAnnotatorPolicy
    from pypy.rpython.test.test_llinterp import get_interpreter

    # first annotate, rtype, and backendoptimize PyPy
    interp, graph = get_interpreter(entry_point, [], backendopt=True,
                                    config=config,
                                    policy=PyPyAnnotatorPolicy(space))

    # parent process loop: spawn a child, wait for the child to finish,
    # print a message, and restart
    while True:
        child_pid = os.fork()
        if child_pid == 0:
            break
        os.waitpid(child_pid, 0)
        print '-' * 79
        print 'Child process finished, press Enter to restart...'
        raw_input()

    from pypy.jit.tl.pypyjit_child import run_child
    run_child(globals(), locals())


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        # debugging: run the code directly
        entry_point()
    else:
        test_run_translation()
