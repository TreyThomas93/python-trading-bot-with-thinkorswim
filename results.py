
from enum import Enum
from json_database import JsonDatabase
import pandas as pd
from tabulate import tabulate

"""
View results of strategies based on closed positions.

Values include:
    - count: number of positions
    - profitLoss: total profit/loss of positions
"""

closedPositions = []
with JsonDatabase('closed_positions', f'lib/src/data/closed_positions.conf') as db:
    for position in db:
        closedPositions.append(position)


positions = {}
for position in closedPositions:
    strategy = position["strategy"]
    entryPrice = position["entryPrice"]
    exitPrice = position["exitPrice"]

    if strategy not in positions:
        positions[strategy] = {
            'count': 1,
            'profitLoss': exitPrice - entryPrice,
        }

    else:
        positions[strategy]['count'] += 1
        positions[strategy]['profitLoss'] += exitPrice - entryPrice

df = pd.DataFrame.from_dict(positions, orient='index')

df.sort_values(by=['profitLoss'], inplace=True, ascending=False)

df['profitLoss'] = df['profitLoss'].apply(lambda x: f'${x:.2f}')


class TableFormat(Enum):
    ###########################################################
    # https: // github.com/astanin/python-tabulate#table-format
    ###########################################################
    PLAIN = "plain"
    SIMPLE = "simple"
    GITHUB = "github"
    GRID = "grid"
    SIMPLE_GRID = "simple_grid"
    ROUNDED_GRID = "rounded_grid"
    HEAVY_GRID = "heavy_grid"
    MIXED_GRID = "mixed_grid"
    DOUBLE_GRID = "double_grid"
    FANCY_GRID = "fancy_grid"
    OUTLINE = "outline"
    SIMPLE_OUTLINE = "simple_outline"
    ROUNDED_OUTLINE = "rounded_outline"
    HEAVY_OUTLINE = "heavy_outline"
    MIXED_OUTLINE = "mixed_outline"
    DOUBLE_OUTLINE = "double_outline"
    FANCY_OUTLINE = "fancy_outline"
    PIPE = "pipe"
    ORGTBL = "orgtbl"
    ASCIIDOC = "asciidoc"
    JIRA = "jira"
    PRESTO = "presto"
    PRETTY = "pretty"
    PSQL = "psql"
    RST = "rst"
    MEDIAWIKI = "mediawiki"
    MOINMOIN = "moinmoin"
    YOUTRACK = "youtrack"
    HTML = "html"
    UNSAFEHTML = "unsafehtml"
    LATEX = "latex"
    LATEX_RAW = "latex_raw"
    LATEX_BOOKTABS = "latex_booktabs"
    LATEX_LONGTABLE = "latex_longtable"
    TEXTILE = "textile"
    TSV = "tsv"


print(tabulate(df, headers='keys',
      tablefmt=TableFormat.SIMPLE_GRID.value))
