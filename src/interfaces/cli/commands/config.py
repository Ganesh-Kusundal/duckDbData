"""
Configuration management CLI commands.
"""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import json

# Import with fallback handling
try:
    from duckdb_financial_infra.infrastructure.logging import get_logger
    from duckdb_financial_infra.infrastructure.config.settings import get_settings
except ImportError:
    try:
        # Try relative imports for development
        from ...infrastructure.logging import get_logger
        from ...infrastructure.config.settings import get_settings
    except ImportError:
        # Final fallback
        import logging
        get_logger = lambda name: logging.getLogger(name)
        get_settings = lambda: None

logger = get_logger(__name__)
console = Console()


@click.group()
@click.pass_context
def config(ctx):
    """Configuration management commands."""
    pass


@config.command()
@click.option('--section', help='Show specific configuration section')
@click.option('--format', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@click.pass_context
def show(ctx, section, format):
    """Show current configuration."""
    verbose = ctx.obj.get('verbose', False)

    try:
        settings = get_settings()

        if section:
            # Show specific section
            if hasattr(settings, section):
                section_data = getattr(settings, section)
                display_config_section(section, section_data, format)
            else:
                console.print(f"[red]❌ Configuration section '{section}' not found[/red]")
                available_sections = [attr for attr in dir(settings) if not attr.startswith('_')]
                console.print(f"[yellow]Available sections: {', '.join(available_sections)}[/yellow]")
        else:
            # Show all sections
            display_full_config(settings, format)

    except Exception as e:
        logger.error(f"Failed to show configuration: {e}")
        console.print(f"[red]❌ Failed to show configuration: {e}[/red]")
        raise click.Abort()


@config.command()
@click.argument('key')
@click.argument('value')
@click.option('--section', help='Configuration section')
@click.pass_context
def set(ctx, key, value, section):
    """Set a configuration value."""
    verbose = ctx.obj.get('verbose', False)

    if verbose:
        console.print(f"[bold blue]⚙️  Setting configuration: {key} = {value}[/bold blue]")

    try:
        # This is a simplified implementation
        # In a real system, you'd want to update the actual config files
        console.print("[yellow]⚠️  Configuration persistence not yet implemented[/yellow]")
        console.print(f"[blue]Would set {key} = {value} in section '{section or 'default'}'[/blue]")

        # TODO: Implement actual configuration file updates
        console.print("[red]❌ Configuration updates are not yet supported[/red]")
        console.print("[dim]This feature requires implementation of configuration file management[/dim]")

    except Exception as e:
        logger.error(f"Failed to set configuration: {e}")
        console.print(f"[red]❌ Failed to set configuration: {e}[/red]")
        raise click.Abort()


@config.command()
@click.argument('config_file', type=click.Path(exists=True))
@click.option('--validate-only', is_flag=True, help='Only validate configuration without applying')
@click.pass_context
def load(ctx, config_file, validate_only):
    """Load configuration from file."""
    verbose = ctx.obj.get('verbose', False)

    if verbose:
        console.print(f"[bold blue]📁 Loading configuration from: {config_file}[/bold blue]")

    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)

        if validate_only:
            console.print("[green]✅ Configuration file is valid JSON[/green]")
            return

        # TODO: Implement actual configuration loading
        console.print("[yellow]⚠️  Configuration loading not yet implemented[/yellow]")
        console.print(f"[blue]Would load {len(config_data)} configuration items[/blue]")

    except json.JSONDecodeError as e:
        console.print(f"[red]❌ Invalid JSON in configuration file: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        console.print(f"[red]❌ Failed to load configuration: {e}[/red]")
        raise click.Abort()


@config.command()
@click.argument('output_file', type=click.Path())
@click.option('--format', type=click.Choice(['json', 'yaml']), default='json',
              help='Output format')
@click.pass_context
def export(ctx, output_file, format):
    """Export current configuration to file."""
    verbose = ctx.obj.get('verbose', False)

    if verbose:
        console.print(f"[bold blue]📤 Exporting configuration to: {output_file}[/bold blue]")

    try:
        settings = get_settings()

        # Convert settings to dictionary
        config_dict = {}
        for attr in dir(settings):
            if not attr.startswith('_') and not callable(getattr(settings, attr)):
                value = getattr(settings, attr)
                # Convert complex objects to basic types
                if hasattr(value, '__dict__'):
                    config_dict[attr] = value.__dict__
                else:
                    config_dict[attr] = value

        # Write to file
        with open(output_file, 'w') as f:
            if format == 'json':
                json.dump(config_dict, f, indent=2, default=str)
            else:
                # TODO: Implement YAML export
                console.print("[yellow]⚠️  YAML format not yet supported, using JSON[/yellow]")
                json.dump(config_dict, f, indent=2, default=str)

        console.print(f"[green]✅ Configuration exported to: {output_file}[/green]")

    except Exception as e:
        logger.error(f"Failed to export configuration: {e}")
        console.print(f"[red]❌ Failed to export configuration: {e}[/red]")
        raise click.Abort()


@config.command()
@click.pass_context
def validate(ctx):
    """Validate current configuration."""
    verbose = ctx.obj.get('verbose', False)

    try:
        settings = get_settings()

        validation_results = []
        issues_found = 0

        # Check database configuration
        if hasattr(settings, 'database'):
            db_config = settings.database
            if not db_config.path:
                validation_results.append(("database.path", "ERROR", "Database path is not set"))
                issues_found += 1
            else:
                db_path = Path(db_config.path)
                if not db_path.parent.exists():
                    validation_results.append(("database.path", "WARNING", f"Database directory does not exist: {db_path.parent}"))
                    issues_found += 1

        # Check logging configuration
        if hasattr(settings, 'logging'):
            log_config = settings.logging
            if hasattr(log_config, 'file') and log_config.file.enabled:
                log_path = Path(log_config.file.path)
                if not log_path.parent.exists():
                    validation_results.append(("logging.file.path", "WARNING", f"Log directory does not exist: {log_path.parent}"))
                    issues_found += 1

        # Display results
        if issues_found == 0:
            console.print("[green]✅ Configuration validation passed![/green]")
        else:
            console.print(f"[yellow]⚠️  Configuration validation found {issues_found} issues:[/yellow]")

            table = Table()
            table.add_column("Setting", style="cyan")
            table.add_column("Level", style="magenta")
            table.add_column("Issue", style="red")

            for setting, level, issue in validation_results:
                level_color = "red" if level == "ERROR" else "yellow"
                table.add_row(setting, f"[{level_color}]{level}[/{level_color}]", issue)

            console.print(table)

    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        console.print(f"[red]❌ Configuration validation failed: {e}[/red]")
        raise click.Abort()


def display_config_section(section_name, section_data, format):
    """Display a specific configuration section."""
    console.print(f"[bold blue]⚙️  Configuration Section: {section_name}[/bold blue]")

    if format == 'json':
        console.print(json.dumps(section_data.__dict__ if hasattr(section_data, '__dict__') else section_data, indent=2, default=str))
    else:
        table = Table()
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        if hasattr(section_data, '__dict__'):
            for key, value in section_data.__dict__.items():
                if not key.startswith('_'):
                    table.add_row(key, str(value))
        else:
            for key, value in section_data.items() if isinstance(section_data, dict) else []:
                table.add_row(key, str(value))

        console.print(table)


def display_full_config(settings, format):
    """Display the full configuration."""
    if format == 'json':
        config_dict = {}
        for attr in dir(settings):
            if not attr.startswith('_') and not callable(getattr(settings, attr)):
                value = getattr(settings, attr)
                if hasattr(value, '__dict__'):
                    config_dict[attr] = value.__dict__
                else:
                    config_dict[attr] = value

        console.print(json.dumps(config_dict, indent=2, default=str))
    else:
        # Display sections
        sections = [attr for attr in dir(settings) if not attr.startswith('_') and not callable(getattr(settings, attr))]

        for section in sections:
            section_data = getattr(settings, section)
            display_config_section(section, section_data, format)
            console.print()  # Add spacing between sections
