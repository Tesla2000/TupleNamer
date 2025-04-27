## Running

You can run script with docker or python

### Python
```shell
python main.py --config_file src/tuple_namer/config_sample.toml
```

### Cmd
```shell
poetry install
poetry run tuple_namer
```

### Docker
```shell
docker build -t TupleNamer .
docker run -it TupleNamer /bin/sh
python main.py
```
