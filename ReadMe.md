# LitErotica training dataset v2 (JSON) by jorfl

This repo is a (slightly fixed) copy of jorfl's scrape of LitErotica website. Specifically, it's a:
- second version of this scrape;
- JSON-format edition.

### What's fixed
Due to some bug, the dataset contains garbage entries, with a ton of html/js instead of regular prose.
I've fixed (almost) all such entries in `Gay` category.

Other than that, the repo is published here simply for ease of auto-download with python.

Source: https://gitgud.io/jorfl/novelai/-/blob/master/README.template.md

Original download link on `mega`: https://mega.nz/folder/opxHRYYa#PNMKS9LQ6ldR3HCDlqts0g/file/J4I0SLIL

This repo comes in tandem with [my `literotica` python package](https://github.com/Lex-DRL/literotica-PyPackage) designed to filter/sort the dataset easily to buld a custom story selection. And that package is actually the primary reason for this repo to exist.

So I believe, the following text from the original dataset author isn't the best way to work with it anymore. But to give a credit, here it is, still:

## Note from the original repo

---

### Working with the JSON LitErotica dump
https://mega.nz/folder/opxHRYYa#PNMKS9LQ6ldR3HCDlqts0g/file/J4I0SLIL

The JSON format LitErotica dump is intended to be used by coders for their own projects. Here's a quick overview on how to use it.

Schema:
* `categories.json`
	* List of categories. Keyed by category, and includes:
		* `category`, `description`, `url`, `page_links`
* `<category>_stories.json`
	* List of stories in this category. Note `\` in the `<category>` is replaced by `&` in the filename. Keyed by story id, and includes:
		* `id`, `title`, `url`, `category`, `rating`, `description`, `keywords`, `text`, `page_count`, `word_count`, `author`, `date_approved`
* `<category>_keywords_top.json`
	* List of keywords (aka tags) that are most common in this category. Keyed by keyword.
		* Array of story ids.
* `keywords_top_overall.json`
	* Same as the above, but for the top overall keywords.

Example code to process all stories:
```python
import json

if __name__ == "__main__":
	# Load categories
	with open( "categories.json", "r", encoding="utf-8") as i:
		categories_list = list(json.load(i).keys())
	print(f"{len(categories_list)} categories found.")

	# Now process stories by each category
	for category in categories_list:
		print(f"Processing {category}...")

		# Note this replacement so that the categories are valid filenames
		category = category.replace("/"," & ")

		stories_file = "%s_stories.json" % category

		# Load the stories for this category
		with open(stories_file, "r", encoding="utf-8") as i:
			stories = list(json.load(i).values())
		print(f"{len(stories)} stories found.")
		
		# Process each story
		for story in stories:
			print(f"{story['title']}, length {len(story['text'])}, tags [{','.join(story['keywords'])}]")

```