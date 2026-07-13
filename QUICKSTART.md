# Quick start

```bash
pip install -e ".[dev]"
pytest -q
python examples/basic_usage.py
```

```python
from rrann import Generator

g = Generator(seed=2.4)          # remainder mode, drop=2
print(g.random())
print(g.randbits(64))
print(g.randbytes(16).hex())
```

Legacy float (old demos):

```python
import rrann
print(rrann.generate(2.4))
```

Optional terminal demo:

```bash
pip install rich
python examples/demo_terminal.py
```
