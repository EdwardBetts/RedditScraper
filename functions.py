import datetime
from datetime import timezone
import math
import pyperclip
import curses
import webbrowser
import search
import json
import dump
import formatString
import scroll



def currentTimestamp():
    return datetime.datetime.now(timezone.utc).replace(tzinfo=timezone.utc).timestamp()


def getSearches(JSONPath):
    searches = []
    with open(JSONPath,"r") as read:
        data = json.load(read)
        s = data["searches"]
        read.close()

        for item in s:
            subs = item["subreddits"]
            subSearches = []
            for i in subs:
                name = i["name"]
                titleWL = i["whiteListTitle"]
                titleBL = i["blackListTitle"]
                flairWL = i["whiteListFlair"]
                flairBL = i["blackListFlair"]
                postWL = i["whiteListPost"]
                postBL = i["blackListPost"]
                subSearches.append(search.SubredditSearch(name,titleWL,titleBL,flairWL,flairBL,postWL,postBL))

            searches.append(search.Search(item["name"],item["lastSearchTime"],subSearches))
    
    return searches

"""
reddit is the reddit instance, searchCriteria is a search object, and numPosts is the number of posts to fetch per subreddit in
searchCriteria

"""
def getNumPosts(reddit, searchCriteria, numPosts = 20):
    posts = []
    for sub in searchCriteria.subreddits:
        subreddit = reddit.subreddit(sub.subreddit)
        for post in subreddit.new(limit=numPosts):
            posts.append(post)

    return posts




"""
Return values:
    -2 searches is empty
    -1 user pressed q to quit
    >=0 the index of the searches list that was chosen

"""
def getSearchNum(screen, searches):
    if(searches):
        ls = []
        ticker = 1
        for item in searches:
            ls.append(f"{ticker}. {item.name}")
            ticker = ticker + 1
        
        toolTip = scroll.ToolTip(formatString.combineStrings("<-- Line 1 -- >","(press q to quit)",80,0,curses.COLS-18))
        page = scroll.ScrollingList(screen,ls,0,toolTip)
        lineNum = 0
        while(True):
            screen.clear()
            
            ticker = 0
            for item in page.getLines():
                screen.addstr(ticker,0,f"{item}")
                ticker = ticker + 1
            

            screen.refresh()
            char = screen.getch()
            if(char == ord('q')):
                return -1
            
            elif(char == curses.KEY_UP or char == ord('w')):
                page.scrollUp()
                toolTip.replace([formatString.combineStrings(f"<-- Line {lineNum + 1} -- >","(press q to quit)",80,0,curses.COLS-18)])
            
            elif(char == curses.KEY_DOWN or char == ord('s')):
                page.scrollDown()
                toolTip.replace([formatString.combineStrings(f"<-- Line {lineNum + 1} -- >","(press q to quit)",80,0,curses.COLS-18)])
            
            elif char == ord('e'):
                # Updates prompt
                toolTip.replace([formatString.combineStrings(f"Enter a post number, then press enter: ","(press q to exit)",80,0,curses.COLS-18)])
                screen.clear()
            
                ticker = 0
                for item in page.getLines():
                    screen.addstr(ticker,0,f"{item}")
                    ticker = ticker + 1
                

                screen.refresh()
                screen.addstr(curses.LINES-1,39,"") # Moves cursor to end of prompt
    

                # Display what they type, and require they press enter
                c = screen.getch() # Allows immediate exit if they press q
                if c == ord('q'):
                    toolTip.replace([formatString.combineStrings(f"<-- Line {lineNum + 1} -- >","(press q to quit)",80,0,curses.COLS-18)])
                    continue
                toolTip.replace([formatString.combineStrings(f"Enter a post number, then press enter: ","(enter q to quit)",80,0,curses.COLS-18)])
                ticker = 0
                for item in page.getLines():
                    screen.addstr(ticker,0,f"{item}")
                    ticker = ticker + 1
                

                screen.refresh()
                screen.addstr(curses.LINES-1,39,"") # Moves cursor to end of prompt
                curses.echo()
                curses.nocbreak()
                curses.ungetch(c) # Adds the first character back to the buffer
                string = screen.getstr()

                # Undo displaying input and requiring enter be pressed
                curses.noecho()
                curses.cbreak()

                # Ensures that their input is an integer
                val = 0
                try:
                    val = int(string)
                except ValueError:
                    
                    continue
                

                val -= 1
                if(val >= 0 and val < len(searches)):
                    screen.clear()
                    screen.refresh()
                    return val
                toolTip.replace([formatString.combineStrings(f"<-- Line {lineNum + 1} -- >","(press q to quit)",80,0,curses.COLS-18)])
        return -1
    else:
        return -2
            

def performSearch(reddit,search):
    posts = []
    for sub in search.subreddits:
        subreddit = reddit.subreddit(sub)
        for post in subreddit.new(limit=None):
            if(post.created_utc < search.lastSearchTime):
                break
            else:
                if(filterPost(post,sub)):
                    posts.append(post)
    
    return posts

def filterPost(post,subReddit):
    return True


def enableScrolling(stringList):
    return True


def copyToClipboard(string):
    pyperclip.copy(string)

def getInput(prompt, lowerBound, upperBound, numAttempts = -1):
    if(lowerBound < 0  or upperBound < 0):
        return -1
    attempts = 0
    if(numAttempts <= 0):
        attempts = numAttempts - 1
    while(attempts < numAttempts):
        try:
            value = int(input(f"{prompt}\n"))
        except ValueError:
            attempts += 1
            continue
        return value
    return -1


def viewPost(post,screen):
    age = f"Created {formatString.formatAge(int(currentTimestamp()-post.created_utc))} ago"
    stringList = formatString.enboxList([post.title,age,"%separator%",post.selftext,"%separator%",post.url],curses.COLS)
    postLessThanFull = False
    if(len(stringList) < curses.LINES - 2):
        postLessThanFull = True
    
    postLineNum = 0

    page = scroll.ScrollingList(screen,stringList,0,[scroll.Row(curses.LINES-1,curses.COLS-38,"(press h for help)  (press q to exit)",curses.COLS)])
            
    while(True):
        screen.clear()
        ticker = 0
        for item in page.getLines():
            screen.addstr(ticker,0,f"{item}")
            ticker = ticker + 1

        if(postLessThanFull or postLineNum == len(stringList) - curses.LINES + 3):
            screen.addstr(curses.LINES-1,0,f"<-- (end) -->")
        else:
            screen.addstr(curses.LINES-1,0,f"<-- Line {postLineNum+1} -->")

        screen.refresh()
        char = screen.getch()
        
        if char == ord('q'):
            break
        elif(char == ord('s')):
            page.scrollDown()
        elif(char == ord('w')):
            page.scrollUp()
        elif char == ord('h'):
            screen.addstr(3,0,"yo")
            while(True):
                screen.clear()
                helpPage = scroll.ScrollingList(screen,["Press the button in () to execute its command",
                                                        "(w) or (up arrow) scroll up",
                                                        "(s) or (down arrow) scroll down",
                                                        "(h) Displays this menu",
                                                        "(o) Opens the post in a new tab of the default web browser",
                                                        "(c) Copies the post url to the clipboard",
                                                        "(u) Prints the post url to the screen (You will have to manually copy it)",
                                                        "(a) Opens the author's page in a new tab of the default web browser",
                                                        "(q) returns to the previous screen",
                                                        "Press any key to exit this screen"],0,None)
                
                ticker = 0
                for item in helpPage.getLines():
                    screen.addstr(ticker,0,f"{item}")
                    ticker = ticker + 1
                screen.refresh()
                char = screen.getch()
                if char == ord('q'):
                    break
                elif(char == ord('s')):
                    helpPage.scrollDown()
                elif(char == ord('w')):
                    helpPage.scrollUp()

        elif char == ord('o'):
            webbrowser.open_new_tab(post.url)
        elif char == ord('c'):
            copyToClipboard(post.url)
        elif char == ord('a'):
            webbrowser.open_new_tab(f"https://www.reddit.com/user/{post.author.name}/")
        elif char == ord('u'):
            screen.clear()
            screen.addstr(0,0,post.url)
            screen.addstr(curses.LINES-1,curses.COLS-18,"(press q to exit)")
            screen.addstr(curses.LINES-1,0,"")
            screen.refresh()
            while(char != ord('q')):
                char = screen.getch()


