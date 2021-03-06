from setuptools import setup

setup(name='finance',
      version='0.1',
      description='Command line tool for tracking spending',
      url='https://github.com/stefankopieczek/finance',
      author='Stefan Kopieczek',
      license='LGPLv2',
      packages=['finance'],
      package_data= {
        "finance": [
          "logging.conf"
        ]},
      zip_safe=False,
      entry_points = {
          'console_scripts': [
              'finance=finance.main:repl',
              'finance-store=finance.main:ingest_file',
          ]
      }
      )
