import os.path
import sys


if __name__ == '__main__':
    selfpath = os.path.dirname(os.path.abspath(__file__))
    rootpath = os.path.join(selfpath, '..')
    sys.path.append(rootpath)

    from transer import daemon
    daemon.init()
