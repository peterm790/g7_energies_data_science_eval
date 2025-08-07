# Web scraping commodities

![demonstration](demo.gif)

**not sure why the gif is so slow, much faster in real life :)*

I have done some web scraping in the past, but I found this very challenging. I suppose this should not be surprising as tradingeconomics.com are in the business of selling this data. 

Initially I used dev mode on google chrome to analyse the network traffic and found the chart data was being loaded from `https://d3ii0wo49og5mi.cloudfront.net/markets/lc:com?span=max&ohlc=0&key=20240229:nazare` but after decoding the base64 contents I found the data was compressed and encrypted. Looking at the javascript in the page sources it seems the data is compressed using `https://github.com/nodeca/pako`, which I believe is equivalent to `zlib`. The real challenge is that the data is also encrypted using `https://github.com/jedisct1/libsodium`. The data is being decrypted on the server side so I suppose it must be possible but I could not work out how to reliable extract the encryption key. 

So not wanting to get too bogged down on this, I chose the easy way out, automate the downloading of SVG files using `selenium` and then write a custom script to extract the data from the SVG graphs to a pandas dataframe. It still needs some refinement. For instance I know the weekly data is reported on Fridays so this could be used to more accurately report the dates. I have also only extracted the 10y data. It would be possible to use this same technique to automate the scraping of daily data for each 6 month period over tha last x years. 

to run:

```
python3 -m venv v-env # init a virtual env from a python installation
source v-env/bin/activate # activate v-env
pip install -r requirements.txt # install requirements
python3 get_data_v2.py # run script
```

I assume you would need chrome installed for this to run properly. Other than that selenium seems to run happily straight out the box. 