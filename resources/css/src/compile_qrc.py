import os

def compile_all():
    files = os.listdir('.')
    for f in files:
        if os.path.isdir(f) and os.path.exists(os.path.join(f, "style.qss")):
            print("Compiling for PyQt5: pyrcc5 %s/style.qrc -o ../%s.py" % (f,f))
            os.system("pyrcc5 %s/style.qrc -o ../%s.py" % (f,f))

if __name__ == "__main__":
    compile_all()
