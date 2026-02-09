# Honoka v3 
(Previously C2N: Confluence HTML → Notion)
- Cross-platform: macOS + Linux
-- App Works on windows but haven't tested the file path and naming issues
- Images and exported files kept local; served via Notion api during import (aws/gcs cdn approach was disabled)
- Tables with images converted to Notion column_list/column; wrap rows >6 cells
- Use HTML <title> as Notion page title
- Option to strip off unwanted, repeated shown domain space name in title for each page. 

## GUI

You only need to have nodejs installed, no need for python because I bundled it in each release. Many people don't have python needed for their daily work so they will be torubled on how to installed that just to used this tool. 

The 3 tabs for honoka.

### Analyze 
This is the function to get insight for selected Knowledge base. 
Material (media types, size)
Table counts (merged)
Layout (2 column, 3 column, 1/3 etc)
Template serial no. 
Contributors 

### Github Markdown (conversion)
Most engineering teams have their solid repos. But their project docs are sacttered in confluence, notion, github, jira, figma, slack, etc.



### Notion Import 
This is the old C2N. It was using cdn (aws/gcs) for bulk migration and keep correct layouts, table for orginal confluence pages. 
After fixing a security issue, the cdn approach was disabled/removed. Even with GCP impersonate, unless company grantd a user 24hr of temp public for bucket ,migrate large media is impossible. 
Current Notion import is using notion native api so file size is limited to less 20mb. Some domain knowledge spaces with larger files, such as mobile QA videos, certain diagrams, that will be left over in confluence if you run notion imoprpt with this tool.

The cdn approach was introduced becaue we found asking people to archive before manually migrating is impractical. It's a huge waste of thousands of people's precious work hours in several Qs for entire company.  


See [README_ELECTRON.md](README_ELECTRON.md) for details.

## Config
- GUI stores config at `~/.notion_importer/config.json`.
- CLI flags override config.
