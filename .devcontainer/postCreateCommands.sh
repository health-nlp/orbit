uv run -m pip install /pybool_ir/pylucene/dist/lucene-10.0.0-cp313-cp313-linux_x86_64.whl.whl
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 JCC_JDK=${JAVA_HOME} JCC_ARGSEP=";" JCC_LFLAGS="-L$JAVA_HOME/lib;-ljava;-L$JAVA_HOME/lib/server;-ljvm;-Wl,-rpath=$JAVA_HOME/lib:$JAVA_HOME/lib/server" JCC="python -m jcc --wheel" uv add /pybool_ir/pylucene/jcc
uv run -m pip install /pybool_ir