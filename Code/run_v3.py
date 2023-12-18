from io import BytesIO
import asyncio # pip install asyncio
import aiofiles
import aiohttp
import requests # pip install requests
import html
import io
import re
import os
import random
import shutil
import json

CONNECTION_COUNT = 20

async def get_story(session, story, asyncio_semaphore, wordcount_limit=10000, page_limit=1):
    async with asyncio_semaphore:
        try:
            # Construct a request
            async with session.get(story["url"], headers = {'User-agent': 'Mozilla/5.0'}) as resp:
                if resp.status == 200:
                    try:
                        resp.raise_for_status()
                        result = await resp.text()
                        
                        content = html.unescape(result)

                        if "<title data-rh=\"true\">" in content:
                            # Parse the story
                            #story["title"] = content.split("<title data-rh=\"true\">")[-1].split("<")[0].split("-")[0].strip()
                            story["description"] = content.split("name=\"description\" content=\"")[-1].split("\"")[0]
                            story["keywords"] = content.split("name=\"keywords\" content=\"")[-1].split("\"")[0].split(",")
                            story["keywords"] = list(set([x.strip().lower() for x in story["keywords"] if len(x) > 1])) # clean up and normalize tags
                            story["text"] = clean_up_story(content.split("<div class=\"aa_ht\"><div>")[-1].split("</div>")[0])
                            story["page_count"] = int(content.split("\"pages_count\":")[-1].split("}")[0])
                            story["word_count"] = int(content.split("\"words_count\":")[-1].split(",")[0])
                            story["author"] = content.split("\"authorname\":\"")[-1].split("\"")[0]
                            story["date_approved"] = content.split("\"date_approve\":\"")[-1].split("\"")[0]

                            # Check story filters
                            if story["word_count"] > wordcount_limit:
                                return None
                            if story["page_count"] > page_limit:
                                return None
                            

                            # Download and append the rest of the pages
                            for i in range(2,story["page_count"]+1):
                                page_url = "%s?page=%i" % (story["url"], i)
                                async with session.get(page_url, headers = {'User-agent': 'Mozilla/5.0'}) as resp:
                                    if resp.status == 200:
                                        try:
                                            resp.raise_for_status()
                                            result = await resp.text()
                                            content = html.unescape(result)
                                            new_page_text = clean_up_story(content.split("<div class=\"aa_ht\"><div>")[-1].split("</div>")[0])
                                            story["text"] += new_page_text
                                        except IOError:
                                            pass # Invalid
                            
                            return story
                        else:
                            print("Title not found in story")
                    except IOError:
                        pass # Invalid
        except Exception as e:
            print(e)
        
        return None # This story will be filtered out


async def get_stories_content(stories):
    results = []
    timeout = aiohttp.ClientTimeout(total=5000)
    asyncio_semaphore = asyncio.BoundedSemaphore(CONNECTION_COUNT) # 30 active downloads at a time
    async with aiohttp.ClientSession(timeout=timeout) as session:
        print("fetching %i stories..." % len(stories))

        tasks = []
        for i in range(len(stories)):
            task = asyncio.create_task(get_story(session, stories[i], asyncio_semaphore))
            tasks.append(task)
        results = await asyncio.gather(*tasks)
    
    # Remove failed searches
    results = [x for x in results if x is not None]

    print("Done story download!")
    
    return results


async def get_content(session, url, asyncio_semaphore):
    async with asyncio_semaphore:
        try:
            # Construct a request
            async with session.get(url, headers = {'User-agent': 'Mozilla/5.0'}) as resp:
                if resp.status == 200:
                    try:
                        resp.raise_for_status()
                        result = await resp.text()
                        return result
                    except IOError:
                        pass # Invalid image
                return None
        except Exception as e:
            print(e)
            return None

async def get_content_async(urls):
    results = []
    timeout = aiohttp.ClientTimeout(total=5000)
    asyncio_semaphore = asyncio.BoundedSemaphore(CONNECTION_COUNT) # 30 active downloads at a time
    async with aiohttp.ClientSession(timeout=timeout) as session:
        print("fetching %i urls..." % len(urls))

        tasks = []
        for i in range(len(urls)):
            task = asyncio.create_task(get_content(session, urls[i], asyncio_semaphore))
            tasks.append(task)
        results = await asyncio.gather(*tasks)
    
    # Remove failed searches
    results = [x for x in results if x is not None]
    
    return results

def cleanhtml(raw_html):
  cleanr = re.compile('<.*?>')
  cleantext = re.sub(cleanr, '', raw_html)
  return cleantext

def clean_up_story(story):
    story = html.unescape(story)
    story = story.replace("\r", "\n")
    story = re.sub("[^\S\n]+/gm", " ", story)
    story = re.sub(" +,/g", ",", story)
    story = story.replace("“","\"")
    story = story.replace("”","\"")
    story = story.replace("‘","'")
    story = story.replace("’","'")
    story = story.replace("…", "...")
    story = re.sub(" +([,!])/g", "$1", story)
    story = re.sub("^ +([^ ])/gm", "$1", story)
    story = re.sub("([^ ]) +$/gm", "$1", story)
    story = re.sub("^\n+/", "", story)
    story = re.sub("\n+/g", "\n", story)
    story = re.sub("^[^a-z0-9]+$/gm", "***", story)
    return cleanhtml(story.replace("<br>","").replace("<p>","\n")).replace("\n\n","\n").replace("\n\n","\n").replace("\n\n","\n")


def write_story_training_data(subfolder, name, stories, append=False):
    ''' Write these 'stories' to an output named 'name'. This writes to the current folder.'''
    #with open("D:\\Repos\\LitEroticaDownload\\Datasets\\%s.txt" % name,"w") as o:
    name = name.replace("/"," & ")
    name = re.sub('[^\w\-_\. &]', '_', name) # strip suspicious characters
    root = "D:\\Repos\\LitEroticaDownload\\Datasets"
    if not os.path.isdir(root):
        os.makedirs(root)
    if not os.path.isdir("%s\\%s" % (root, subfolder)):
        os.makedirs("%s\\%s" % (root, subfolder))
    
    permission = "w"
    if append:
        permission = "a"
    with open("%s\\%s\\%s.txt" % (root, subfolder, name), permission, encoding="utf-8") as o:
        for story in stories:
            o.write("\n\n----- " + story["title"] + " -----\n")
            o.write(story["text"])


def download_and_process_stories(stories, story_sampling_byrating_or_byrandom="byrating", max_number_of_stories=100, max_tags_per_category=100):
    ''' Process the specified categories, downloading all their stories
        Returns:
            (stories augmented with story details, keywords_top)
     '''
    # Filter to a subset of the stories for this category based on rating
    if story_sampling_byrating_or_byrandom == "byrating":
        stories = dict(sorted(stories.items(), key=lambda x: x[1]["rating"], reverse=True)[:max_number_of_stories])
    elif story_sampling_byrating_or_byrandom == "byrandom":
        stories = dict(sorted(stories.items(), key=lambda x: random.random(), reverse=True)[:max_number_of_stories])
    
    # Download these stories async
    print("Downloading stories...")
    asyncio.set_event_loop(asyncio.SelectorEventLoop())
    stories_unindexed = asyncio.get_event_loop().run_until_complete(get_stories_content(list(stories.values())))

    # Re-index stories
    stories = {}
    for story in stories_unindexed:
        stories[story["id"]] = story

    # Count the keywords
    keyword_counts = {}
    for story_key in stories.keys():
        story = stories[story_key]
        for keyword in story["keywords"]:
            if keyword in keyword_counts:
                keyword_counts[keyword].append(story["id"])
            else:
                keyword_counts[keyword] = [story["id"]]
    
    
    # Update the base category top keyword list
    keywords_top = dict(sorted(keyword_counts.items(), key=lambda x: len(x[1]), reverse=True)[:max_tags_per_category])

    return (stories, keywords_top)




if __name__ == "__main__":
    # Scrape the Literotica stories
    s = requests.session()

    # Grab the catgories
    r = s.get("https://www.literotica.com/stories/", headers = {'User-agent': 'Mozilla/5.0'})
    text = r.text.split("<b>Stories By Category</b>")[-1].split("<b>Special Sections</b>")[0]
    sections = text.split("<a href=\"")
    categories = {}
    print("--- Category listing ---")
    story_link_path = "story_list.json"
    category_path = "categories.json"
    if os.path.exists(category_path):
        print("Loading existing categories...")
        with open(category_path, "r", encoding="utf-8") as i:
            categories = json.load(i)
    else:
        for section in sections:
            if section.startswith("http"):
                category = {
                        "category" : html.unescape(section.split("size=\"3\">")[1].split("<")[0]),
                        "description" : html.unescape(section.split(" - </font>")[1].split("<")[0]),
                        "url" : section.split("\"")[0],
                        "stories": [],
                    }
                
                # Grab the link to the top-rated stories in the category
                r = s.get(category["url"] + "/1-page", headers = {'User-agent': 'Mozilla/5.0'})
                if "https://www.literotica.com/stories/" in r.text:
                    print(category["url"])

                    # Parse the page links
                    page_links_unparsed = r.text.split("<select name=\"page\">")[-1].split("</select>")[0].split("value=\"")
                    page_links = []
                    for page_link in page_links_unparsed[1:-1]:
                        page_links.append("%s/%s-page" % (category["url"], page_link.split("\"")[0]))
                    category["page_links"] = list(set(page_links))

                    categories[category["category"]] = category
                    #if len(categories) >= 4:
                    #    break # TODO: REMOVE ME

        #print(categories)
        with open(category_path, "w", encoding="utf-8") as o:
            o.write( json.dumps(categories) )

    print("%i categories found." % len(categories))

    # Now grab the story links
    story_link_path = "story_list.json"
    if os.path.exists(story_link_path):
        print("Loading existing stories...")
        with open(story_link_path, "r", encoding="utf-8") as i:
            stories = json.load(i)
        with open("story_list_by_category.json", "r", encoding="utf-8") as i:
            stories_by_category = json.load(i)
    else:
        minimum_rate = 4.0
        stories = {}
        stories_by_category = {}
        for category_key, category in categories.items():
            # Bulk download the story list pages
            print("--- Downloading stories and pre-processing for %s ---" % category_key)
            print("Downloading story listing pages...")
            stories_for_category = {}
            story_ids = []
            asyncio.set_event_loop(asyncio.SelectorEventLoop())
            pages_html = asyncio.get_event_loop().run_until_complete(get_content_async(category["page_links"]))

            # Add the story list urls per category
            print("Processing story listing pages...")
            for page in pages_html:
                sections = page.split("<div class=\"b-story-list\">")[-1].split("<div class=\"b-pager\">")[0].split("<div class=\"b-sl-item-r w-34t\">")

                for section in sections:
                    if "<a href=\"https://www.literotica.com/s/" in  section and "<span class=\"b-sli-rating\">" in section:
                        story_id = section.split("<a href=\"https://www.literotica.com/s/")[-1].split("\"")[0]
                        url_story = "https://www.literotica.com/s/" + story_id
                        rating = float(section.split("<span class=\"b-sli-rating\">")[-1].split("</span>")[0])
                        title = section.split(" class=\"r-34i\">")[-1].split("<")[0]

                        # Very aggressively remove multi-part stories
                        title_lower = title.lower()
                        is_chapter = False
                        '''
                        if "pt." in title_lower:
                            is_chapter = True
                        if "ch." in title_lower:
                            is_chapter = True
                        if " ch" in title_lower:
                            is_chapter = True
                        if "chapter" in title_lower:
                            is_chapter = True
                        if "vol" in title_lower:
                            is_chapter = True
                        '''
                        
                        # Remove any stories with 1 or more digits
                        numbers = sum(c.isdigit() for c in title_lower)
                        if numbers > 0:
                            is_chapter = True

                        if is_chapter == False:
                            if story_id not in stories_for_category and rating >= minimum_rate:
                                stories_for_category[story_id] = {
                                    'id': story_id,
                                    "title": title,
                                    "url":url_story,
                                    "category":category["category"],
                                    "rating":rating,
                                }
                                story_ids.append(story_id)
                #break # TODO: REMOVE ME
            print("Found %i total stories for category %s." % (len(stories_for_category), category_key))
            stories.update(stories_for_category)
            stories_by_category[category_key] = story_ids

        with open(story_link_path, "w", encoding="utf-8") as o:
            json.dump(stories, o)
        with open("story_list_by_category.json", "w", encoding="utf-8") as o:
            json.dump(stories_by_category, o)
    
    print("%i total stories after processing." % len(stories))

    # Now build the overall top keywords across all categories. We do this by random sampling 10000 stories
    print("--- Downloading and processing top overall tags by random sampling ---")
    keywords_top_overall_path = "keywords_top_overall.json"
    if os.path.exists(keywords_top_overall_path):
        print("Loading existing top overall keywords...")
        with open(keywords_top_overall_path, "r", encoding="utf-8") as i:
            keywords_top_overall = json.load(i)
    else:
        (stories_random, keywords_top) = download_and_process_stories(stories, "byrandom", max_number_of_stories=20000, max_tags_per_category=5000 )
        del stories_random

        # Select top N overall tags to track
        keywords_top_overall = dict(sorted(keywords_top.items(), key=lambda x: len(x[1]), reverse=True)[:2000])

        with open(keywords_top_overall_path, "w", encoding="utf-8") as o:
            json.dump(keywords_top_overall, o)

    print(keywords_top_overall.keys())
    
    if os.path.isdir("D:\\Repos\\LitEroticaDownload\\Datasets\\By Tag"):
        shutil.rmtree("D:\\Repos\\LitEroticaDownload\\Datasets\\By Tag")

    # Now download all stories per category, producing the final output
    print("--- Downloading and processing each category ---")
    for category_key, category in categories.items():
        # Build set of stories in this category
        story_ids = stories_by_category[category_key]
        stories_in_category = {}
        for story_id in story_ids:
            stories_in_category[story_id] = stories[story_id]
        
        # Download these stories
        stories_in_category_path = "%s_stories.json" % (category_key.replace("/", " & "))
        keywords_top_path = "%s_keywords_top.json" % (category_key.replace("/", " & "))
        if os.path.exists(stories_in_category_path):
            print("Using existing stories and keywords...")
            with open(stories_in_category_path, "r", encoding="utf-8") as i:
                stories_in_category = json.load(i)
            with open(keywords_top_path, "r", encoding="utf-8") as i:
                keywords_top = json.load(i)
        else:
            (stories_in_category, keywords_top) = download_and_process_stories( stories_in_category, "byrating", max_number_of_stories=40000, max_tags_per_category=300 )
            with open(stories_in_category_path, "w", encoding="utf-8") as o:
                json.dump(stories_in_category, o)
            with open(keywords_top_path, "w", encoding="utf-8") as o:
                json.dump(keywords_top, o)

        # Write the stories to disk
        print("Writing %i stories per for category to disk" % len(stories_in_category))
        write_story_training_data("By Category",category_key, list(stories_in_category.values()))
        
        # Write per-category with keyword
        print("Writing per category per keyword data...")
        for keyword, story_ids in keywords_top.items():
            stories_with_keyword = []
            for story_id in story_ids:
                stories_with_keyword.append( stories_in_category[story_id] )
            
            # Write the stories in training format
            write_story_training_data("By Category With Specific Tag\\%s" % category_key,  keyword, stories_with_keyword)

        # Write per-keyword data
        print("Writing per keyword data...")
        for keyword, junk in keywords_top_overall.items():
            stories_with_keyword = []
            for story in stories_in_category.values():
                if keyword in story["keywords"]:
                    stories_with_keyword.append(story)
            
            if len(stories_with_keyword) > 0:
                write_story_training_data("By Tag", keyword, stories_with_keyword, append=True)

