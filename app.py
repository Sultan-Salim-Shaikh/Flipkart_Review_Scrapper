from flask import Flask, render_template, request, redirect
from bs4 import BeautifulSoup as soup
from flask_cors import CORS, cross_origin
import requests 
import pymongo 
import pandas as pd 
import numpy as np
import os 
import shutil
import random
import string

some_queue = None

app = Flask(__name__)

# Global Path 
CSVs_path = os.path.join('static', 'CSVs')


# Global Varibles 
base_URL = "https://flipkart.com"

dic = {
     "title" : [],
     "review" : [],
     "user_name" : [],
     "rating" : []
} 


def get_prod_HTML(productLink=None) : 
    '''
    make the url request and fetch the data (HTML)
    '''
    prod_page_HTML = requests.get(productLink)
    return soup(prod_page_HTML.text, "html.parser")


def get_product_links(bigBoxes=None):
	'''
	returns the product link so we make the request to particular products
	'''
	# temporary list to return the results
	temp = []
	# iterate over list of bigBoxes
	for box in bigBoxes:
		try:
			# if prod name and list present then append them in temp
			temp.append(base_URL + box.div.div.a["href"])
		except:
			pass
	return temp



def comment_box_page_review_link(prod_page_HTML=None) :
    '''
    fetch the content of the pages and return the link of page that contain all reviews 
    '''
    # find all reviews link that redirect to review pages
    all_review_link_div = prod_page_HTML.find("div", {"class" : "_3UAT2v"})
    # review page links 
    reviews_link = base_URL + all_review_link_div.find_parent()['href'] 
    return reviews_link

 
def extract_reviews(review_link, no_of_review = 10, page_length = 10) :

    # Base Case 
    if (page_length == 0 or no_of_review == 0) :
        return dic

    prod_review_page_HTML = get_prod_HTML(review_link)
    all_review_divs = prod_review_page_HTML.findAll("div", {"class": "K0kLPL"})
    print("review link sucess !!!")

    for one_box in all_review_divs :
            """
                store the info in dictionary
            """
            if (no_of_review == 0) :
                break
            try :
                title = one_box.div.p.get_text()
                dic['title'].append(title)
            except :
                dic['title'].append("No Title")
            try :
                review = one_box.find(class_ = "_6K-7Co").get_text() 
                dic['review'].append(review)
            except :
                try : 
                    review = one_box.find(class_ = "").get_text()
                    dic['review'].append(review)  
                except : 
                    dic['review'].append("No Review")
            try :
                user_name = one_box.find(class_ = "_2V5EHH").get_text()
                dic['user_name'].append(user_name)
            except :
                dic['user_name'].append("No Username")
            try :
                rating = one_box.find(class_ = "_3LWZlK").get_text()
                dic['rating'].append(rating)
            except :
                dic['rating'].append("No rating") 
            no_of_review = no_of_review - 1
        
    next_review_link = ""
    # where next and page button is present
    list_length = len(prod_review_page_HTML.find_all("a", {"class" : "_1LKTO3"}))
        
    if(list_length == 1) :
        '''
        Get the link of next button if len=1
        we are at home page
        '''
        route_url = prod_review_page_HTML.find_all("a", {"class" : "_1LKTO3"})[0]['href']
        next_review_link = base_URL + route_url   
    elif(list_length == 2):
        '''
        we have two button prev and next 
        '''
        route_url = prod_review_page_HTML.find_all("a", {"class" : "_1LKTO3"})[1]['href']
        next_review_link = base_URL + route_url
    
    return extract_reviews(next_review_link,no_of_review, page_length - 1)


def clean_CSV_files(path):
    '''
        To clean the previous file present in the CSVs directory
    '''
    if os.listdir(path) != list() :
        files = os.listdir(path)
        print(files)
        for fileName in files : 
            print(fileName)
            os.remove(os.path.join(path, fileName))
    else :
        return 


def random_string() :
    '''
        It Generate a random name for the product when search
        by link 
    '''

    letters = string.ascii_lowercase
    randomString = ''.join(random.choice(letters) for i in range(10))
    return randomString


@app.route("/")
@cross_origin()
def home() :
    '''
        Index page route that render the index.html file 
    '''
    return render_template("index.html")


@app.route("/result", methods = ["GET", "POST"]) 
# @cross_origin
def result() : 
    
    if request.method == "POST" :
        search_string = request.form['searchString'] # need to make a collections name = search_string
        search_string = search_string.replace(" ", "") # input = "real me" then "realme"  

        try : 

                # Concate the base-URL + Search Product Ex: https://flipkart/search?q=productName
                url = base_URL + "/search?q=" + str(search_string)
                print(url)
                
                try : 
                    prod_page_HTML = get_prod_HTML(url)
                    print("we have data")
                except : 
                    print("no data !!")

                product_link_boxes = prod_page_HTML.find_all("div", {"class":"_13oc-S"})
                # print(product_link_boxes)
                # Store the product link in list of search product 
                product_link_list = get_product_links(product_link_boxes)
                # print(product_link_boxes)

                # iterate over the strings and find the link url 
                for link in product_link_list[: 1] :
                    # get the html or each links 
                    prod_page_HTML = get_prod_HTML(link)
                    review_link = comment_box_page_review_link(prod_page_HTML)
                    extract_reviews(review_link)
                
                print("review scrapped......")
                data = pd.DataFrame.from_dict(dic) 

                path = CSVs_path
                
                clean_CSV_files(path)

                data.to_csv(os.path.join(path, search_string + ".csv"), index=False) 
                dic['title'].clear()
                dic['review'].clear()
                dic['user_name'].clear()
                dic['rating'].clear()

                return render_template('result.html', reviews = data, file_name = search_string + ".csv")
       
        except Exception as error: 
           
            error = "Our review scrapper cann't scraps this product could you checkout other items :)"
            return render_template('index.html', error=error)
    else :
        # restart()
        return redirect('/')

@app.route("/result-by-link", methods = ["GET", "POST"])
# @cross_origin
def resultByLink() : 
    if request.method == "POST" :
        try :
            link = request.form['searchStringLink']
            
            no_of_review = int(request.form['noOfReview'])
            print(no_of_review)

            prod_page_HTML = get_prod_HTML(link)
            review_link = comment_box_page_review_link(prod_page_HTML)
            print(review_link)
            
            extract_reviews(review_link, no_of_review)
            data = pd.DataFrame.from_dict(dic)

            path = CSVs_path

            fileName = random_string()
            
            clean_CSV_files(path)

            data.to_csv(os.path.join(path, fileName + ".csv"), index=False) 
            dic['title'].clear()
            dic['review'].clear()
            dic['user_name'].clear()
            dic['rating'].clear()

            return render_template('result.html', reviews = data, file_name =  fileName + ".csv")
       
        except Exception as error: 
            error = "Our review scrapper cann't scraps this product could you checkout another product item :)"
            return render_template('index.html', error=error)
    else :
        return redirect('/')

@app.route("/about")
# @cross_origin
def about() :
    return render_template("about.html")
# handle the non existing urls 
@app.errorhandler(404)
def page_not_found(e):
    return redirect("/")


if __name__ =='__main__':
    app.run(debug=True)
	