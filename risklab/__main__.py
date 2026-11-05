import sys
if __name__ == '__main__':
    if '--headless' in sys.argv:
        from .cli import main
        main([x for x in sys.argv[1:] if x!='--headless'])
    else:
        from .ui.application import main
        main()
