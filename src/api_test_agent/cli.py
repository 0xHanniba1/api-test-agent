"""CLI entry point for api-test-agent."""

from pathlib import Path

import click

from api_test_agent.parser.base import ApiEndpoint
from api_test_agent.parser.detect import detect_format
from api_test_agent.parser.swagger import parse_openapi
from api_test_agent.parser.postman import parse_postman
from api_test_agent.generator.testcase import TestCaseGenerator
from api_test_agent.generator.code import CodeGenerator


def _parse_doc(file_path: Path, fmt: str) -> list[ApiEndpoint]:
    """Parse API document based on format."""
    if fmt == "auto":
        fmt = detect_format(file_path)

    if fmt == "swagger":
        return parse_openapi(file_path)
    elif fmt == "postman":
        return parse_postman(file_path)
    else:
        from api_test_agent.parser.markdown import parse_markdown
        return parse_markdown(file_path)


@click.group()
def main():
    """API Test Agent — generate test cases and automation code from API docs."""
    pass


@main.command()
@click.argument("doc_path", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", required=True, type=click.Path(path_type=Path), help="Output file path for test cases Markdown.")
@click.option("--depth", default="quick", type=click.Choice(["quick", "full"]), help="Test depth level.")
@click.option("--model", default=None, help="LLM model to use.")
@click.option("--format", "fmt", default="auto", type=click.Choice(["auto", "swagger", "postman", "markdown"]), help="Document format.")
def gen_cases(doc_path: Path, output: Path, depth: str, model: str | None, fmt: str):
    """Generate test case document from API documentation."""
    click.echo(f"Parsing {doc_path} (format: {fmt})...")
    endpoints = _parse_doc(doc_path, fmt)
    click.echo(f"Found {len(endpoints)} endpoints.")

    click.echo(f"Generating test cases (depth: {depth})...")
    gen = TestCaseGenerator(model=model)
    result = gen.generate(endpoints, depth=depth)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result, encoding="utf-8")
    click.echo(f"Test cases saved to {output}")


@main.command()
@click.argument("cases_path", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", required=True, type=click.Path(path_type=Path), help="Output directory for generated code.")
@click.option("--model", default=None, help="LLM model to use.")
def gen_code(cases_path: Path, output: Path, model: str | None):
    """Generate pytest+requests code from test case document."""
    click.echo(f"Reading test cases from {cases_path}...")
    testcases = cases_path.read_text(encoding="utf-8")

    click.echo("Generating code...")
    gen = CodeGenerator(model=model)
    files = gen.generate(testcases)

    output.mkdir(parents=True, exist_ok=True)
    for filename, content in files.items():
        file_path = output / filename
        file_path.write_text(content, encoding="utf-8")
        click.echo(f"  Created {file_path}")

    click.echo(f"Generated {len(files)} files in {output}")


@main.command()
@click.argument("doc_path", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", required=True, type=click.Path(path_type=Path), help="Output directory for all generated files.")
@click.option("--depth", default="quick", type=click.Choice(["quick", "full"]), help="Test depth level.")
@click.option("--model", default=None, help="LLM model to use.")
@click.option("--format", "fmt", default="auto", type=click.Choice(["auto", "swagger", "postman", "markdown"]), help="Document format.")
def run(doc_path: Path, output: Path, depth: str, model: str | None, fmt: str):
    """Full pipeline: parse doc -> generate test cases -> generate code."""
    # Step 1: Parse
    click.echo(f"Parsing {doc_path} (format: {fmt})...")
    endpoints = _parse_doc(doc_path, fmt)
    click.echo(f"Found {len(endpoints)} endpoints.")

    # Step 2: Generate test cases
    click.echo(f"Generating test cases (depth: {depth})...")
    tc_gen = TestCaseGenerator(model=model)
    testcases = tc_gen.generate(endpoints, depth=depth)

    output.mkdir(parents=True, exist_ok=True)
    cases_path = output / "testcases.md"
    cases_path.write_text(testcases, encoding="utf-8")
    click.echo(f"  Test cases saved to {cases_path}")

    # Step 3: Generate code
    click.echo("Generating code...")
    code_gen = CodeGenerator(model=model)
    files = code_gen.generate(testcases)

    for filename, content in files.items():
        file_path = output / filename
        file_path.write_text(content, encoding="utf-8")
        click.echo(f"  Created {file_path}")

    click.echo(f"Done! Generated {len(files) + 1} files in {output}")
