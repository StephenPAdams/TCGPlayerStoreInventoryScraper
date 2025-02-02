# History
When making Magic: The Gathering decks, we're often faced with a scenario: We need cards for our deck that we don't have, and we ask ourselves if we want to wait days to obtain cards from TCGPlayer OR whether we should make a trip to our LGS (Local Game Store) to acquire said cards...if they even have them.

Now, some of our LGSs sell singles on TCGPlayer. That's great. You can even bulk add cards to your cart through their Mass Entry tool located [here](https://www.tcgplayer.com/massentry). However, that Mass Entry tool is only available on TCGPlayer.com, and not on the individual storefront URLs that the game stores have through their Pro program. Which means if you want to see what cards your LGS has in their inventory, you'll need to do an individual search for each and every card on the store's TCGPlayer Pro store site. That stinks.

So, the first avenue I went down to solve this problem is to see if TCGPlayer's API could solve these issues. I created a developer account years ago as I was going to make a website tied around tracking booster box pricing and individual cards to appropriately gauge box to set EV without having to rely on other websites which often didn't have every set or every box type (set, play, collector, etc.). So, I never got around to doing that, but I still had a developer account. Which is a good thing because they are no longer granting new API access. 

So I dug into the developer documentation, and fired up CURL and tried to pull a store's inventory and was met with many access issues. Turns out that individual stores need to give you permission via their store authorization flow. Needless to say, that's a show stopper for the API, as I'm not going to reach out to every store and ask them to click a link, give permissions to their storefront to some rando M:TG player. So I had to find another avenue. 

Well, that other avenue is scraping. While, some of the code is still in this codebase to hit TCGPlayer's API, mainly to try and grab store information and storefront URLs, but it's not really needed for this repository's use case at this time.

What this code does is the following:

1. Goes through the storefront's site and scrapes their M:TG inventory: card name, treatment, set, rarity, quantity available, condition/language, price, image URL, and product detail URL. 
2. It, optionally, takes in a file of wanted cards (simply the quantity and name of the card delimited gby a space)
3. At the end of the scrape, it dumps all of the inventory into an Excel file with 3 worksheets: Store Inventory, Wanted Cards (from the optional file provided), and a Found Cards worksheet that lists all of the store inventory items that match the wanted cards.

# Overview
This script is written in Python, specifically targeting version 3.9.x. Chrome is a required installation otherwise the script will not run. A future version will add a mechanism to auto install Chrome as a dependency to the OS.

It leverages a myriad of libraries, but most importantly:

- Selenium (for automated scraping)
- Pandas (for easy exporting to Excel and basic querying)

# Considerations
This script can run in the background without maintaining focus on the Chrome browser that is opened while scraping is performed.

You might be wondering why this scraper goes through every set in the store's inventory. Well, it's because (and I learned the hard way) that TCGPlayer limits the number of items you can go through the inventory. That number is roughly 10,000 cards. So, when using pagination of 36 per page the top limit is around 277 pages. With 24, it's about 416 pages. And at 48, well, it's at around 208.

Since I'm not aware of a single M:TG set with more than 10k cards in it, going through the sets allows this to fully get the inventory. Alas, it does make it a tad slower as if the store only has 1 card from a set, that is going to do a scrape request for that 1 card compared to a set where they have far more.


# Installation and Usage
There is an optional install.sh script for macOS users and an install.ps1 for Windows users which will download and install the appropriate dependencies that aren't able to be installed by Python, for example: Google Chrome. 

## For macOS
For macOS, from the terminal, run the following command:

    sh install.sh

## For Windows
For Windows, from PowerShell, run the following command:

    .\install.ps1

In the event that you're having permissions issues via PowerShell, you'll want to run this command prior to the install script:

    Set-ExecutionPolicy RemoteSigned

## Install Requirements
Prior to running the script, you'll want to ensure that the dependencies are installed via the following command:

    pip install -r requirements.txt

## Script Usage

    tcg_player_searcher.py -s <store-name> -u <store-url> -w <want-file-location> -h <headless-flag>

*store-url is the TCGPlayer Pro store URL. If provided, store-name will be bypassed and the store URL will be directly used and no API calls will be made to find store information.
*store-name is the official TCG Player store name to look for
*want-file-location is the file location for a list of card names (in a text file) that you're looking to find for the store
*headless-flag is the Selenium/Chrome flag to run headless. Values can be: empty (won't run headless), --headless (old headless for Chrome < v109), and --headless=new for full Chrome but headless (Chrome >= v109)

## Script Example

For example, to run the scraper for the Game Haven store with the desired cards in a txt file using the new Chrome headless mode, you'd use the following command:

    tcg_player_searcher.py -u "https://mdgamehaven.tcgplayerpro.com/" -w "desired_cards_example.txt" -h --headless=new


# Exported Files
At the end of this script, it'll export 1 file

- tcg_player_inventory_for_store.xlsx

Yes, I need to dynamically change the name of the file output so it includes the store name and date/time of the run. That'll be a future improvement. I should probably also put the run details in a worksheet within the file. 