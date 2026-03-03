Creating fake wikipedia page with different contents 
- different formats 
- Wiki Frame for Survey, as close as possible 

Otree Sruvey with pop up, and then floating close button
- web tracking in 
- keep people on the one page or let them move freely 

## Running script: 
```bash
python wiki_converter.py "https://en.wikipedia.org/wiki/Nanjing_massacre" relative_path/nanjing_massacre.html --offline`  
````

***
## Features: 
- changed footer with fake and university disclaimer 
- removed banners
- tracking metrics 

## Problems: 
- different languages have different formats, should work for all
- currently filtering out different objects and parts which are unwanted
- mutiple tabs error breaking survey - same session link ??
 