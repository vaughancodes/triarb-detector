from dataclasses import dataclass
import octobot_commons.symbols as symbols

@dataclass
class ShortTicker:
    symbol: symbols.Symbol
    reversed: bool = False


def find_all_rotations(cycle):
    # Generate all rotations of the cycle
    return [cycle[i:] + cycle[:i] for i in range(len(cycle))]