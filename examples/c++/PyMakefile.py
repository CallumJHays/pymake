from pymake.pymake import Dependencies
import pymake as mk


@mk.writes('%.o', '%.cpp')
def unix():
    pass

@mk.command
def make():
    pass


if __name__ == "__main__":
    run()
