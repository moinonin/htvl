# HTVL 
This is a compiler that can aid you to write HTML files faster. It can also be used to write cgi files in a convenient way. For example: First prepare your project directory as follows:
.  
├── assets  
│   ├── img  
│   │   ├── github.png  
│   │   ├── htvl-logo.png  
│   │   └── inzpiro_web.png  
│   └── proto.css  
├── htvl-compiler.sh  
├── index.htvl  
├── public  
│   ├── assets  
│   │   ├── img  
│   │   │   ├── github.png  
│   │   │   ├── htvl-logo.png  
│   │   │   └── inzpiro_web.png  
│   │   └── proto.css  
│   └── index.html  
└── templates  
    ├── footer.sh  
    ├── headtags.sh  
    └── nav.sh  
Where all files are as they are in the project upon clonning or downlading. 

# Usage
The file with extension .htvl are the kind of files you will need to write in order to generate HTML. If you are only writing cgi the files should be executable the way .htvl file is. An example hello world htvl can be written as:  

```  
$(h 3 '' '' 'Official Sponsor') 
```
Save this as yourFileName.htvl inside the project root directory
Within the directory run the file htvl-compiler

```
$ ./htvl-compiler.sh 
```
Of course you have to make it executable first
This will produce

```
<h3 class="" id="" style="">Official Sponsor</h3> 
```    
You can duplicate this for all of you projects. It is faster, error free when all attention is paid, and enables you to write short code


