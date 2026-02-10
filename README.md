# Honoka v3 
(Previously C2N: Confluence HTML → Notion)
- Cross-platform: macOS + Linux
- App Works on windows but haven't been widely tested for file naming/path issues
- Images and exported files kept local; served via Notion api during import (aws/gcs cdn approach was disabled)
- Tables with images converted to Notion column_list/column; wrap rows >6 cells
- Option to strip off unwanted, repeated shown domain space name in html title for each doc. 

## GUI

You only need to have nodejs installed, no need for python because I bundled it in each release. Many people don't have python needed for their daily work so they will be torubled on how to installed that just to used this tool. 

The 3 tabs for honoka.

### Analyze 
This is the function to get insight for selected Knowledge base. We use score like this to calcualte and auto deprecate pages. Many pages are silently abandoned. 
$$
Score = \log(Versions) × \frac{Silence}{Active Span + 1}
$$

Metadata like these are necessary, but some of them are not accessible in new platforms such as Notion. New formula may need to be revised. 
- Material (media types, size, image counts)
- Table counts (merged & detail)
- Layout (2 column, 3 column, 1/3 etc)
- Template serial no. 
- Last edit date
- Created date
- Contributors 
- Outbound link counts

It has a leaderboard feature shows who contributed and maintained most docs. Thise encourages responsible and capable people gardening their domain docs during their time in this company. Such appraoch is based on the fact that our attention resource is limited. 

The feature was implanted with confluence html export so needs revision to meet Notion api capabilities.

Use GET /v1/pages/{page_id} in Notion to obtain a JSON :

- last_edited_time: (ISO 8601 format) 
- last_edited_by : Username（User ID）。
- created_time
- created_by


There's no version counts in original notion api. So further adjustment in db field is needed to make data retrievable.
Detail recorded in roadmap for honoka.md  

### Github Markdown (conversion)
Most engineering teams have their solid repos. But their project docs are sacttered in confluence, notion, github, jira, figma, slack, etc. This feature helps them convert docs into github flavor markdown. Diagrams can be hosted directly on github. Very helpful to keep images, diagrams and necessary docs closely attached to their functions. Making them curosr AI accessible & up-to-date wihtout being bloated. 


### Notion Import (Render & Migration)
This is the legacy C2N. It was using cdn (aws/gcs) for bulk migration and keep layouts (images within table,etc) from orginal confluence pages correct. This can minimaize manual intervention and ensure Notion AI can utilze doc in their right way, not gibberish.   
However the cdn approach was disabled/removed after fixing a security issue. Even with GCP impersonate, unless company grants a user 24hr of temp public permission for a GCS bucket, migrate large media is impossible. 
Current Notion import function is using notion native api so file size is limited to less 20mb. Some domain knowledge spaces with larger files, such as mobile QA videos, certain diagrams, that will be left over in confluence if you run notion imoprpt with this tool.

The cdn approach was introduced becaue we found asking people to archive outdated conlfuence pages before manually migrating is impractical. It's a huge waste on thousands of people's precious work hours in several Qs for multiple companies.  


See [README_ELECTRON.md](README_ELECTRON.md) for details.

## Config
- GUI stores config at `~/.notion_importer/config.json`.
- CLI flags override config.
