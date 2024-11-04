import time
from item import paragraph
import requests
from responce_init import ScrapeOpsFakeBrowserHeaderAgentMiddleware
from bs4 import BeautifulSoup
from clustering import clusters
globL_time=time
start=globL_time.time()
#
# def get_linkes(rss):
#     rss_feed_url=rss
#     middleware = ScrapeOpsFakeBrowserHeaderAgentMiddleware()
#
#     request = requests.Request('GET', rss_feed_url)
#
#     middleware.process_request(request)
#
#     with requests.Session() as session:
#         response = session.send(request.prepare())
#     soup = BeautifulSoup(response.content, 'xml')
#
#     items = soup.find_all('item')
#
#     links = [item.find('link').text for item in items]
#     return links
# urls=(get_linkes("http://newsrss.bbc.co.uk/rss/newsonline_world_edition/front_page/rss.xml"))
url="https://english.ahram.org.eg/NewsContent/1/1234/534652/Egypt/Foreign-Affairs/Egypt-urges-all-parties-to-avoid-regional-escalati.aspx"
if __name__ == '__main__':
  for url in url:
    print(url)
    x = paragraph(url)

    start_time = time.time()  # Start time before get_cleaned()
    cleaned_text = x.get_cleaned()
    end_time = time.time()  # End time after get_cleaned()
    clean_time = end_time - start_time
    print(f"Cleaned Text:\n{cleaned_text}")
    print(f"Time to clean: {clean_time:.4f} seconds\n")  # Print time with 4 decimal places
#
#     start_time = time.time()  # Start time before get_title()
#     title = x.get_title()
#     end_time = time.time()  # End time after get_title()
#     title_time = end_time - start_time
#     print(f"Title: {title}")
#     print(f"Time to get title: {title_time:.4f} seconds\n")  # Print time with 4 decimal places
#
#     start_time = time.time()  # Start time before get_cat()
#     category = x.get_cat()
#     end_time = time.time()  # End time after get_cat()
#     cat_time = end_time - start_time
#     print(f"Category: {category}")
#     print(f"Time to get category: {cat_time:.4f} seconds\n")  # Print time with 4 decimal places
#     start_time = time.time()  # Start time before get_cat()
#     img = x.get_img()
#     end_time = time.time()  # End time after get_cat()
#     cat_time = end_time - start_time
#     print(f"images: {img}")
#     print(f"Time to get category: {cat_time:.4f} seconds\n")  # Print time with 4 decimal places
#
#     start_time = time.time()  # Start time before get_summary()
#     summary = x.get_summary()
#     end_time = time.time()  # End time after get_summary()
#     summary_time = end_time - start_time
#     print(f"Summary:\n{summary}")
#     print(f"Time to get summary: {summary_time:.4f} seconds")  # Print time with 4 decimal places
# end=globL_time.time()
#
# print("Total Time",(end-start)/60)



# app = FastAPI()
#
# @app.post("/generate_paragraph")
# async def generate_paragraph(url: str = Body(...)):
#     x = paragraph("https://www.bbc.com/arabic/articles/cw0vr5g2qz9o")
#
#     cleaned_text = x.get_cleaned()
#     title = x.get_title()
#     category = x.get_cat()
#     summary = x.get_summary()
#
#
#     return {
#         "cleaned_text": cleaned_text,
#         "title": title,
#         "category": category,
#         "summary": summary,
#         "total_time": total_time
#     }
#
# if __name__ == "__main__":
#     uvicorn.run("main:app", host="0.0.0.0", port=8000)
