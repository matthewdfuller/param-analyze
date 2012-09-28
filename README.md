#Param-analyze

##Overview
Param-analyze came about because I was looking for a very quick and simple way to check URLs for potential XSS flaws. While there are many scanners,
proxies, and fuzzers on the market that do just this, param-analyze is extremely simple to use and does not require any proxy configuration, addons,
etc. Param-analyze does not determine if a parameter is vulnerable to XSS, but rather provides information to the user to allow him or her to make
the final decision. The script will scan the URL, and for each reflected occurence of a parameter in the returned code, test if quotes, single quotes,
brackets, and tags are properly filtered.

##Usage
Param-analyze is run from the command line by using the full URL, with the parameter changed to the keyword. This is currently "CHECKME" but can be
changed by editing the keyword constant in the script.

```
$python paramanalyze.py "http://site.com/page.php?param=CHECKME"
```

##What Can Param-analyze Find?
Param-analyze will scan the provided URL parameter and test for:
* Double quotes
* Single quotes
* Left and right angle brackets
* Slashes
* Script and image tags
* Other potential XSS payloads

##Limitations
Being light-weight, Param-analyze is *not* meant to detect XSS vulnerabilities by itself. It will simply tell the user whether certain characters are properly escaped.
Some recommendations are made, but it is ultimately up to the user to further test the site.

##Future Features
* Add POST support
* Make a verbose mode to show users exactly what is happening behind the scenes.