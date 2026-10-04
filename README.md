<p align="center">
  <a href="https://github.com/lupaxa-developers-toolbox">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/organisations/developers-toolbox/readme-logo.png" alt="Developers Toolbox" />
  </a>
</p>

<h1 align="center">Markdown Converter</h1>

Python library that loads CommonMark, GitHub Flavored Markdown, or
Obsidian Markdown into one document tree, then writes any of those
flavours. Conversion is two-pass through that tree — there are no
pairwise converters.

The PyPI name is `lupaxa-markdown-converter`. The import path is
`lupaxa.markdown_converter`. `lupaxa` is a namespace package. The
console script is `markdown-converter`.

## Install

```bash
pip install lupaxa-markdown-converter
```

Requires Python 3.10+. The package pulls in `markdown-it-py`.

You can also run `python -m lupaxa.markdown_converter`.

## Usage

```python
from lupaxa.markdown_converter import MarkdownConverter

source = "[[folder/My Page#Hello World]]\n"
converter = MarkdownConverter(source, flavour="obsidian")

print(converter.to_commonmark())
print(converter.to_github())
print(converter.to_obsidian())
```

`MarkdownConverter` accepts a document string. Set `flavour` to the
flavour of that string (case-insensitive). The value is stored
lower-case on `converter.flavour`, then any `to_*` method can write
it out. Same-flavour conversion is supported.

| `flavour`    | Input                                                                 |
| ------------ | --------------------------------------------------------------------- |
| `commonmark` | CommonMark (default)                                                  |
| `github`     | GitHub Flavored Markdown: tables, tasks, strikethrough, and autolinks |
| `obsidian`   | Those GitHub extras, plus wikilinks, embeds, highlights, and callouts |

```python
from_commonmark = MarkdownConverter("# Title\n", flavour="commonmark")
from_github = MarkdownConverter("- [x] done\n", flavour="github")
from_obsidian = MarkdownConverter("==hi==\n", flavour="OBSIDIAN")
```

> **Note:** Output is canonical. A same-flavour conversion can still
> change the source. A setext heading becomes an ATX heading, and a
> reference link is written inline.

```python
MarkdownConverter("Title\n=====\n", flavour="commonmark").to_commonmark()
# '# Title\n'
```

### Wikilinks and Embeds

An Obsidian wikilink becomes a Markdown link on the way to GitHub or
CommonMark. Each path segment is percent-encoded, `.md` is added when
the target does not already end in `.md`, and a heading becomes a
fragment. An image embed becomes an image. A numeric label is a resize
hint and is dropped. Obsidian keeps both forms.

```python
converter = MarkdownConverter("[[folder/My Page#Hello World]]\n", flavour="obsidian")
converter.to_github()
# '[My Page](folder/My%20Page.md#hello-world)\n'

embed = MarkdownConverter("![[shot.png|100]]\n", flavour="obsidian")
embed.to_github()
# '![shot](shot.png)\n'
embed.to_obsidian()
# '![[shot.png|100]]\n'
```

### Tables, Tasks, and Autolinks

GitHub and Obsidian keep pipe tables, task lists, strikethrough, and
bare autolinks. CommonMark receives the nearest CommonMark form: an
HTML table, escaped checkbox text, `<del>`, and an angle autolink.
Plain CommonMark is left as plain CommonMark. A checkbox written as
ordinary text is escaped, and an HTML table stays HTML.

```python
table = "| A | B |\n| --- | ---: |\n| 1 | 2 |\n"
MarkdownConverter(table, flavour="github").to_obsidian()
# '| A | B |\n| --- | ---: |\n| 1 | 2 |\n'

MarkdownConverter("- [x] done\n", flavour="github").to_github()
# '- [x] done\n'
MarkdownConverter("- [ ] todo\n", flavour="commonmark").to_github()
# '- \\[ \\] todo\n'

MarkdownConverter("~~old~~ and https://example.com\n", flavour="github").to_commonmark()
# '<del>old</del> and <https://example.com>\n'
```

### Highlights and Callouts

Obsidian keeps `==highlights==` and `[!type]` callouts. GitHub and
CommonMark receive `<mark>` and a blockquote whose first line is the
type and title.

```python
note = MarkdownConverter("==hi==\n", flavour="obsidian")
note.to_obsidian()
# '==hi==\n'
note.to_github()
# '<mark>hi</mark>\n'

callout = MarkdownConverter("> [!tip] Look\n", flavour="obsidian")
callout.to_github()
# '> **Tip:** Look\n'
callout.to_obsidian()
# '> [!tip] Look\n'
```

### Frontmatter

A leading YAML fence is copied through unchanged, including its line
endings. The body is converted. The fence is not parsed as Markdown.

```python
source = "---\ntitle: Note\n---\n\n# Title\n"
MarkdownConverter(source, flavour="obsidian").to_commonmark()
# '---\ntitle: Note\n---\n\n# Title\n'
```

### Command Line

`--from` and `--to` are required. They take `commonmark`, `github`, or
`obsidian`. Pass a file, or `-` to read stdin. Omit `-o` to write
stdout.

```bash
markdown-converter --from obsidian --to github note.md -o note.github.md
markdown-converter --from github --to commonmark - < note.md
```

A missing file, a directory, text that is not UTF-8, or a conversion
error prints one `Error:` line on stderr and exits 2.

### Errors

An unknown flavour, a document that is not a string, and a body that
cannot be parsed raise `MarkdownConverterError`. The parse failure is
attached as `__cause__`.

```python
from lupaxa.markdown_converter import MarkdownConverter, MarkdownConverterError

try:
    MarkdownConverter("hi\n", flavour="rst")
except MarkdownConverterError as exc:
    print(exc)
```

<a href="https://github.com/the-lupaxa-project">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/components/footer-for-child-orgs.svg" alt="The Lupaxa Project Footer" width="100%" />
</a>
