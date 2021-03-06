#!/usr/bin/env python

"""
  Python Parameter Analyzer
  A python script for analyzing the potential for XSS using url-provided parameters.
  Copyright: Matthew Fuller, http://matthewdfuller.com
  Usage: python paramanalyze.py "http://site.com/full-path-with-params?param=XSSHEREXSS"
"""
from urlparse import urlparse, parse_qs
from HTMLParser import HTMLParser
from datetime import datetime
import urllib
import urllib2
import sys
import signal
import re

#######################################################################################################################
#GLOBAL VARIABLES
#######################################################################################################################
KEYWORD = "CHECKME"      #Must be plaintext word unlikely to appear on the page natively
RND_START = "JAKSDKSZA"    #Random string to append to check values. If getting errors, try changing or reducing length
RND_END = "KLASKSWLQ"
URL = ""
NUM_REFLECTIONS = 0             #Number of times the parameter value is displayed in the code.

VERBOSE = True

CURRENTLY_OPEN_TAGS = []        #Currently open is modified as the html is parsed
OPEN_TAG = ""                  #Open is saved once xsscheckval is found
OPEN_EMPTY_TAG = ""
TAGS_TO_IGNORE = []             #These tags are normally empty <br/> or should be ignored because don't need to close them but sometimes, not coded properly <br> and missed by the parser.

OCCURENCE_NUM = 0
OCCURENCE_PARSED = 0

CHARS_TO_CHECK = {
    "\"": "Double quote",
    "'": "Single quote",
    "<": "Left angle bracket",
    ">": "Right angle bracket",
    "/": "Normal slash",
    "\\": "Backwards slash"
}

STRINGS_TO_CHECK = {
    "<script>": "<script> script tag is not escaped. There is a strong chance of XSS.",
    "<img />": "<img /> image tag is not escaped. This can be dangerous if additional characters are allowed (see above list).",
    "alert(1);": "alert(1); was not escaped. By itself, this is not too dangerous unless coupled with onmouseover and a double quote."
}

#######################################################################################################################
# MAIN FUNCTION
#######################################################################################################################
def main():
    try:
        #Print an intro comment
        print "\n\tparamanalyze/version 0.1 - parameter analysis tool\n\thttp://matthewdfuller.com\n"
        print "\nLegal Disclaimer: Use of this tool is done at your own risk. You assume all responsibility for its use or the use of any information obtained from its use.\n"
        print "\n[*] starting at " + str(datetime.time(datetime.now())) + "\n"
        
        #Parse the command line arguments
        if (len(sys.argv) != 2 or KEYWORD not in sys.argv[1]):
            printout("fatal", "Invalid usage.\nUsage: python paramanalyze.py <FULL URL REPLACING PARAM TO CHECK WITH " + KEYWORD + ">\nExample: python paramanalyze.py \"http://site.com/?param=" + KEYWORD + "\"\n")
        global URL
        URL = sys.argv[1]
    
        printout("info", "Provided URL: " + URL)
        
        #Load the supplied URL to see if page is valid and can be successfully loaded
        init_resp = make_request(URL)
        printout("info", "URL was successfully loaded.")
        
        if(VERBOSE):
            printout("info", "Response size is: " + str(len(init_resp)) + " characters")
        
        #Now that the URL is valid, see if the response contains the check value (KEYWORD)
        if(VERBOSE):
            printout("info", "Checking if the response contains the test check value.")
        if(KEYWORD.lower() in init_resp.lower()):
            global NUM_REFLECTIONS
            NUM_REFLECTIONS = init_resp.lower().count(KEYWORD.lower())
            printout("info", "Check value was reflected in response " + str(NUM_REFLECTIONS) + " time(s).")
        else:
            printout("fatal", "Check value not in response. Nothing to test.")
        
        #Loop through and run tests for each occurence
        for i in range(NUM_REFLECTIONS):
            print "\n"
            printout("info", "Testing occurence number: " + str(i + 1))
            global OCCURENCE_NUM
            OCCURENCE_NUM = i+1
            test_occurence(init_resp)
            #Reset globals for next instance
            global CURRENTLY_OPEN_TAGS, OPEN_TAG, OCCURENCE_PARSED, OPEN_EMPTY_TAG
            CURRENTLY_OPEN_TAGS, OPEN_TAGS = [], []
            OCCURENCE_PARSED = 0
            OPEN_EMPTY_TAG = ""
        
        printout("exit", "Scan complete.")
    except KeyboardInterrupt:
        printout("exit", "Ctrl+C was pressed.")
    
#######################################################################################################################
# OTHER FUNCTIONS
#######################################################################################################################
#Try various tests against the specific occurence
def test_occurence(init_resp):
    #Begin parsing HTML tags to see where located
    parser = MyHTMLParser()
    location = ""
    try:
        parser.feed(init_resp)
    except Exception as e:
        location = str(e)
    except:
        printout("fatal", "Parsing error. Try rerunning?")
    
    if(location == "comment"):
        printout("info", "Parameter reflected in an HTML comment.")
    elif(location == "script_data"):
        printout("info", "Parameter reflected as data in a script tag.")
    elif(location == "html_data"):
        printout("info", "Parameter reflected as data or plaintext on the page.")
    elif(location == "start_end_tag_attr"):
        printout("info", "Parameter reflected as an attribute in an empty tag.")
    elif(location == "attr"):
        printout("info", "Parameter reflected as an attribute in an HTML tag.")
    else:
        printout("info", "Parameter is on the page but in an obscure location.")

    #Print full tag series leading up to location
    printout("info", "Open tag series preceeding parameter: " + str(CURRENTLY_OPEN_TAGS))
    printout("info", "Last opened tag: " + OPEN_TAG)

    #Begin scanning
    if(test_param_check("'';!--\"<XSS>=&{()}") == "'';!--\"<XSS>=&{()}"):
        printout("info", "Critical risk of XSS. '';!--\"<XSS>=&{()} reflected.")
    else:
        printout("info", "Some filtering is being done. Investigating...")

        for key, value in CHARS_TO_CHECK.iteritems():
            #print item + " and " + CHARS_TO_CHECK[item]
            char_to_check_resp = test_param_check(key)
            if(char_to_check_resp == key):
                printout("warn", value + " is not escaped: " + key)
            else:
                printout("info", value + " is escaped as: " + char_to_check_resp)
                
        for key, value in STRINGS_TO_CHECK.iteritems():
            string_to_check_resp = test_param_check(key)
            if(string_to_check_resp == key):
                printout("warn", value)
            else:
                printout("info", key + " is escaped as: " + string_to_check_resp)

#Tests to see if the param_to_check is reflected in the code as param_to_compare. Can be same or urlescaped.
def test_param_check(param_to_check):
    check_string = RND_START + param_to_check + RND_END
    check_url = URL.replace(KEYWORD, urllib.quote_plus(check_string))
    try:
        check_response = make_request(check_url)
    except:
        check_response = ""
    response = ""
    
    #Loop to get to right occurence
    occurence_counter = 0
    for m in re.finditer(RND_START, check_response, re.IGNORECASE):
        occurence_counter += 1
        if(occurence_counter == OCCURENCE_NUM):
        #if((occurence_counter == OCCURENCE_NUM) and (check_response[m.start():m.start()+len(compare_string)].lower() == compare_string.lower())):
            remaining_str = check_response[m.start():]
            #print remaining_str
            rnd_end_pos = remaining_str.index(RND_END)
            response = remaining_str[len(RND_START):rnd_end_pos]
            break
    return response

#Makes a request to the supplied in_url and returns the response.
def make_request(in_url):
    try:
        req = urllib2.Request(in_url)
        resp = urllib2.urlopen(req)
        return resp.read()
    except:
        printout("fatal", "Could not load the URL. The network could be down or the page may be returning a 404.")

#Prints a message with [INFO] or [WARN] in front along with the current time
def printout(msg_type, msg):
    if(msg_type == "info"):
        print "[" + str(datetime.time(datetime.now())) + "]" + " [INFO] " + msg
    elif(msg_type == "warn"):
        print "[" + str(datetime.time(datetime.now())) + "]" + " [WARNING] " + msg
    elif(msg_type == "fatal"):
        print "[" + str(datetime.time(datetime.now())) + "]" + " [FATAL] " + msg
        print "\n[*] shutting down at " + str(datetime.time(datetime.now())) + "\n"
        exit()
    elif(msg_type == "exit"):
        print "[" + str(datetime.time(datetime.now())) + "]" + " [INFO] " + msg
        print "\n[*] shutting down at " + str(datetime.time(datetime.now())) + "\n"
        exit()
        
#######################################################################################################################
# CLASSES
#######################################################################################################################

#HTML Parser class
class MyHTMLParser(HTMLParser):
    def handle_comment(self, data):
        global OCCURENCE_PARSED
        if(KEYWORD.lower() in data.lower()):
            OCCURENCE_PARSED += 1
            if(OCCURENCE_PARSED == OCCURENCE_NUM):
                raise Exception("comment")
    
    def handle_startendtag(self, tag, attrs):
        global OCCURENCE_PARSED
        global OCCURENCE_NUM
        global OPEN_EMPTY_TAG
        global OPEN_TAG
        if (KEYWORD.lower() in str(attrs).lower()):
            OCCURENCE_PARSED += 1
            if(OCCURENCE_PARSED == OCCURENCE_NUM):
                OPEN_EMPTY_TAG = tag
                OPEN_TAG = tag
                raise Exception("start_end_tag_attr")
            
    def handle_starttag(self, tag, attrs):
        global CURRENTLY_OPEN_TAGS
        global OPEN_TAG
        global OCCURENCE_PARSED
        #print CURRENTLY_OPEN_TAGS
        if(tag not in TAGS_TO_IGNORE):
            CURRENTLY_OPEN_TAGS.append(tag)
            OPEN_TAG = tag
        if (KEYWORD.lower() in str(attrs).lower()):
            if(tag == "script"):
                OCCURENCE_PARSED += 1
                if(OCCURENCE_PARSED == OCCURENCE_NUM):
                    raise Exception("script")
            else:
                OCCURENCE_PARSED += 1
                if(OCCURENCE_PARSED == OCCURENCE_NUM):
                    raise Exception("attr")

    def handle_endtag(self, tag):
        global CURRENTLY_OPEN_TAGS
        global OPEN_TAG
        global OCCURENCE_PARSED
        if(tag not in TAGS_TO_IGNORE):
            CURRENTLY_OPEN_TAGS.remove(tag)
            
    def handle_data(self, data):
        global OCCURENCE_PARSED
        if (KEYWORD.lower() in data.lower()):
            OCCURENCE_PARSED += 1
            if(OCCURENCE_PARSED == OCCURENCE_NUM):
                #If last opened tag is a script, send back script_data
                #Try/catch is needed in case there are no currently open tags, if not, it's considered data (may occur with invalid html when only param is on page)
                try:
                    if(CURRENTLY_OPEN_TAGS[len(CURRENTLY_OPEN_TAGS)-1] == "script"):
                        raise Exception("script_data")
                    else:
                        raise Exception("html_data")
                except:
                    raise Exception("html_data")


#RUN MAIN FUNCTION
if __name__ == "__main__":
    main()