#!/usr/bin/env python3
"""
RRann Interactive Demo - Live terminal visualization of random generation.
Shows histogram, entropy, and statistical properties updating in real-time.
"""

import sys
import time
import math

# For terminal visualization (install: pip install rich)
try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, BarColumn, TextColumn
    from rich.panel import Panel
except ImportError:
    print("Install 'rich' for visualization: pip install rich")
    sys.exit(1)

sys.path.insert(0, '.')
from RRann import generate


class RNGDemo:
    """Live demo of RRann generation with visualization."""

    def __init__(self):
        self.values = []
        self.buckets = [0] * 10
        self.console = Console()
        self.start_time = time.time()

    def update(self, value: float):
        """Record a generated value."""
        self.values.append(value)
        idx = min(9, max(0, int(value * 10)))
        self.buckets[idx] += 1

    def chi_square(self) -> float:
        n = len(self.values)
        if n == 0:
            return 0.0
        expected = n / 10.0
        return sum((b - expected) ** 2 / expected for b in self.buckets)

    def entropy(self) -> float:
        if len(self.values) < 100:
            return 0.0

        bits = []
        for val in self.values[:1000]:
            as_int = int(val * (2**32)) & 0xFFFFFFFF
            for i in range(32):
                bits.append((as_int >> i) & 1)

        if not bits:
            return 0.0

        zeros = bits.count(0)
        ones = bits.count(1)
        total = len(bits)
        p0 = zeros / total
        p1 = ones / total

        entropy = 0.0
        if p0 > 0.0:
            entropy -= p0 * math.log2(p0)
        if p1 > 0.0:
            entropy -= p1 * math.log2(p1)

        return entropy

    def stats(self) -> dict:
        if not self.values:
            return {}

        n = len(self.values)
        mean = sum(self.values) / n
        variance = sum((v - mean) ** 2 for v in self.values) / n

        return {
            'count': n,
            'mean': mean,
            'variance': variance,
            'stdev': math.sqrt(variance),
            'min': min(self.values),
            'max': max(self.values),
            'chi_square': self.chi_square(),
            'entropy': self.entropy(),
            'elapsed': time.time() - self.start_time,
        }

    def render_histogram(self) -> str:
        if not self.values:
            return "No data yet"

        max_bucket = max(self.buckets) if self.buckets else 1
        height = 10
        lines = []

        for row in range(height, 0, -1):
            threshold = (row / height) * max_bucket
            line = ''
            for bucket_val in self.buckets:
                line += '█ ' if bucket_val >= threshold else '  '
            lines.append(f"{threshold:6.0f} │ {line}")

        lines.append('       └' + '─' * 25)
        lines.append('       ' + ''.join(f'{i} ' for i in range(10)))
        return '\n'.join(lines)

    def display(self):
        self.console.clear()
        title = Panel(
            '[bold cyan]RRann: Random Number Generator via Floating-Point Error[/bold cyan]',
            style='bold blue'
        )
        self.console.print(title)
        self.console.print('\n[bold]Distribution (10 buckets, [0, 1) range)[/bold]')
        self.console.print(self.render_histogram())

        s = self.stats()
        if s:
            table = Table(title='Statistics', show_header=True)
            table.add_column('Metric', style='cyan')
            table.add_column('Value', style='green')
            table.add_row('Samples', str(s['count']))
            table.add_row('Mean', f"{s['mean']:.6f}")
            table.add_row('Std Dev', f"{s['stdev']:.6f}")
            table.add_row('Range', f"[{s['min']:.6f}, {s['max']:.6f}]")
            table.add_row('Chi-Square', f"{s['chi_square']:.2f} (< 20 = good)")
            table.add_row('Entropy', f"{s['entropy']:.4f} (1.0 = ideal)")
            table.add_row('Elapsed', f"{s['elapsed']:.1f}s")
            self.console.print(table)

        status = '[bold green]✓ Generating[/bold green]' if self.values else '[yellow]Initializing...[/yellow]'
        self.console.print(f"\n{status}")


def main():
    demo = RNGDemo()
    console = Console()
    console.print('[bold cyan]Starting RRann Demo[/bold cyan]')
    console.print('Generating random values until you stop it with Ctrl+C...\n')

    seed = 2.4
    sample_count = 0

    try:
        with Progress(
            TextColumn('[progress.description]{task.description}'),
            BarColumn(),
            TextColumn('[progress.completed]{task.completed} values'),
            console=console,
        ) as progress:
            task = progress.add_task('[cyan]Generating...', total=None)
            while True:
                value = generate(seed)
                demo.update(value)
                seed = value * 10.0 if value != 0.0 else 1.6180339887498948
                sample_count += 1
                progress.update(task, advance=1)

                if sample_count % 50 == 0:
                    demo.display()
                    time.sleep(0.1)
    except KeyboardInterrupt:
        console.print('\n[bold yellow]Demo stopped by user.[/bold yellow]')
    finally:
        demo.display()
        console.print(f"\n[bold green]Demo ended after {len(demo.values)} values.[/bold green]")


if __name__ == '__main__':
    main()
