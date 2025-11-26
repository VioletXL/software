import os
import sys

def main():

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bool_project.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "异常！"
        )from exc
    execute_from_command_line(sys.argv )


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
