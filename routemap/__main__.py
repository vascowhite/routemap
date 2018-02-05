"""
CLI entry point
"""
from routemap import routemap


def main():
    """
    Get the entry point
    """
    routemap.cli = True
    routemap.routemap()
