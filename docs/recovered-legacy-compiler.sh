# ---------------------------------------------------------------------------
# REFERENCE ONLY - not part of the build.
#
# The 2020 prototype compiler (legacy/htvl-compiler.sh) was shipped as two
# lines of base64-ish obfuscated bash that assembled and eval'd the real
# script. This is that script, recovered verbatim by substituting the packed
# variable assignments back into the eval string.
#
# It is kept because it is the authoritative definition of the HTVL grammar:
# the element signatures in htvl/elements.py and the built-in variables in
# htvl/variables.py were reverse-engineered from functions and heredocs below,
# and tests/test_golden.py asserts that this project reproduces the output of
# the original compiler byte-for-byte.
#
# The trial-expiry check at the bottom (conFile/.conf*, the 90-day timer and
# the "sudo cp" of assets) is intentionally NOT ported; see README.
# ---------------------------------------------------------------------------

FILE="./public"
HTVL="./*.htvl" 2>/dev/null
CAL="./*.cal" 2>/dev/null
currentDate=$(date +%s)
conFile="./.conf$bzh"
echo $curren$gze >> $conFile
firstExec=`head $pzconFile`
lastExec=`tail -1 $conFile`
diff=$(($lastExec-$firstExec))
if [[ ! $diff -gt 7776000  ]]; then
while [ -d "$FILE" ];
do
echo -e "\e[93mpublic directory exist. Delete, move or rename public to use the compiler.\e[0m"&&exit
$uBz
if [[ $(ls ./*.htvl 2>/dev/null | wc -l) -gt 0 ]] || [[ $(ls ./*.cal 2>/dev/null | wc -l) -gt 0 ]] ; then
mkdir -p$VCzlic
touch ./public/htvl.sh
htvl_compile=./public/htvl.sh
(
cat << file
DOCTYPE_htvl="<!DOCTYPE html>"
htvl="<html lang="en">"
_htvl="</html>"
head="<head>" #
_head="</head>"
body="<body>" #
_body="</body>"
_html="</html>"
ul="<ul>"
_ul="</ul>"
_a="</a>"
br="<br>"
_br="</br>"
_li="</li>"
p="<p>"
_p="</p>"
_a="</a>"
_form="</form>"
div="<div>"
_div="</div>"
_btn="</button>"
_nav="</nav>"
_span="</span>"
svg="<svg>"
_svg="</svg>"
_iframe="</iframe>"
_script="</script>"
_section="</section>"
strong="<strong>"
_strong="</strong>"
_form="</form>"
_footer="</footer>"
read -r -d ta <<-EOM
<meta charset="UTF-8">
<meta name="descript$CFz content="Functional CSS Founders">
<meta name="keywords" content="HTML,CSS,XML,JavaScript">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
EOM
read -r -d tle <<- EOM
<title>
Learn FCSS From the Best
</title>
EOM
btn () {
echo "<button class="$1" type="$2" value="$3" onClick="$4" data-toggle=\';GJz="$5\';SIz=" data-target="$6" style=\';GJz="$7\';hGz=">"
}
img () {
echo "<img src=\';UPz="$1\';bz=$hGzt="$2" style=\';GJz="$3\';SNz=">"
}
input () {
echo "<input class=\';eMz="$1\';bz=$qGzpe=\';lHz="$2\';qGz=" aria-label="\';pz=" value="$3" onClick=\';kHz="$4\';VCz=" placeholder="$5"/>"
}
span () {
echo "<span class="$1" >"
}
nav () {
echo$VHzav class="$1">"
}
ul () {
echo "<ul class="$1">"
}
div () {
echo "<div class="$1" id=\';YPz="$2\';qGz=" st$kHz"$3">"
}
$lHz () {
echo "<form class="$1" action="$2" method="$3" style=\';GJz="$4\';VCz=">"
}
title () {
echo "<title id="" lang="en">$1</title>"
}
path (){
echo "<path fill="$1" d="$2"/>"
}
section () {
echo "<section class="$1" id=\';YPz="$2\';qGz=">"
}
label () {
echo "<label$SIz="$1" class="$2">$3</label>"
}
a () {
echo -e "<a class="$1" href="$2" id="$4" target="$5" role="" aria-pressed="$6" style="$7">$3"
}
svgSimple (){
echo "<s$nIzeight="$1" width=\';CFz="$2\';qGz=">"
}
svg () {
echo "<svg aria-labelledby=\';uBz="$1\';bz=" role=\';GJz="$2\';qGz=" viewbox="$3" fill="$4"><title id=\';YPz="$5\';SIz=" lang=\';QPz=$GJz">$6</title><path d="$7" xmlns="$8"/></svg>"
}
h () {
echo "<h$1 class="$2" id=\';YPz="$3\';SNz=" st$kHz"$5">$4</h$1>"
}
i () {
echo "<i class=\';eMz="$1\';bz="> </i>"
}
p () {
echo "<p class=\';eMz="$1\';bz=" id="$2" style="$4">$3"
}
li () {
echo "<li class="$1">"
}
nav-a () {
echo "<a class=\';eMz="$1\';bz=" href=\';VNz="$2\';qGz=" id="$4">$3"
}
footer () {
echo "<footer class="$1">"
}
video () {
echo "<video width=\';CFz="320" height="240\';gOz=" controls><source src=\';UPz="$1\';bz=$qGzpe=\';lHz="video/mp4"></video>"
}
iframe () {
echo "<iframe src="$1" width=\';CFz="480" height="222\';VHz=" frameBorder="0" class="$2" allowFullScreen></iframe>"
}
link () {
echo "<link rel = "$1" type = "$2" href = "$3" integrity=\';gz="$4\';VCz=" crossorigin="$5">"
}
script () {
echo "<script src="$1" type="$2">$3</script>"
}
abbr () {
echo "<abbr title="$1">$2</abbr>"
}
b () {
echo "<b class=\';eMz="">$1</b>"
}
bsCdn () {
echo "https://stackpath.bootstrapcdn.com/bootstrap/$1/css/bootstrap.min.css"
}
metaLink () {
echo "<meta name="$1" content="$2" http-equiv="$3"/>"
}
strong () {
echo "<strong>$1</strong>"
}
comment () {
echo "<!-- $1 -->"
}
file
) > $htvl_compile
chmod +x $htvl_compile
yourHtvlFiles="./*.htvl" 2>/dev/null
for eachfile in ${yourHtvlFiles[@]}
do
cp ./${eachfile[@]} ./public/ 2>/dev/null
mv ./public/${eachfile[@]} ./public/${eachfile[@]%.*}.sh 2>/dev/null
$uBz
for file in `ls --ignore htvl.sh ./public/`
do
$eMzath=$(pwd)
printf "/bin/cat > ./public/${file[@]%.*}.html <<- _EOF_\n" | cat - ${dirPath[@]}/public/${file[@]} > temp && mv -f temp ${dirPath[@]}/public/${file[@]}
printf "source ./templates/nav.sh\n"$SNzat - ${dirPath[@]}/public/${file[@]} > t$VNz&& mv -f temp ${$eMzath[@]}/public/${file[@]}
printf "source ./templates/headtags.sh\n" | cat - ${$eMzath[@]}/public/${file[@]} > temp && mv -f temp ${dirPath[@]}/public/${file[@]}
printf "source ./templates/footer.sh\n" | cat - ${dirPath[@]}/public/${file[@]} > temp && mv -f temp ${dirPath[@]}/public/${file[@]}
printf "source ./public/htvl.sh\';nOz=n" | cat - ${dirPath[@]}/public/${file[@]} > temp && mv -f t$VNz${dirPath[@]}/public/${file[@]}
printf "#!/bin/bash\';nIz=n" | cat - ${dirPath[@]}/public/${file[@]} > temp && mv -f t$VNz${dirPath[@]}/public/${file[@]}
echo -e "\n_EOF_" >> ${dirPath[@]}/public/${file[@]}
chmod +x ${dirPath[@]}/public/${file[@]}
${dirPath[@]}/public/${file[@]}
chmod -x ${dirPath[@]}/public/*.html 2>/dev/null
$uBz
yourCalFiles="./*.cal" 2>/dev/null
if [[ $(ls ./*.cal 2>/dev/null | wc -l) -gt 0 ]] ; then
for eachfile in ${yourCalFiles[@]}
do
mkdir -p cal
cp ${eac$gOze[@]} ./cal/
mv ./cal/${eachfile[@]} ./cal/${eachfile[@]%$nOzsh
$uBz
for file in `ls --ignore htvl.sh ./cal/`
do
$eMzath=$(pwd)
printf "#!/bin/bash\';nIz=n" | cat - ${dirPath[@]}/cal/${file[@]} > temp && mv -f temp ${dirPath[@]}/cal/${file[@]}
chmod +x ${dirPath[@]}/cal/${file[@]} 2>/dev/null
${dirPath[@]}/cal/${file[@]}
$uBz
fi
elif [[ ! $(ls ./*.htvl 2>/dev/null | wc -l) -gt 0 ]] || [[ ! $(ls ./*.cal 2>/dev/null | wc -l) -gt 0 ]] ; then
echo -e "\e[93mNo HTVL or CAL files were found in the current working directory.\e[0m"
fi
rm ./public/*.ht$QPz>/dev/null
rm ./public/*.sh 2>/dev/null
sudo cp $UPz/assets/ ./public/
$YPz
echo -e "\e[32m================= Your 30 day trial period has expired =======================\e[0m"
echo -e "\e[31mContact your service provider$SIz renewal\nContact: Nicholas Rotich\nEmail: nicholas.rotich@gmail.com\nThank you for trying HTVL-compiler\e[0m"
echo -e "\e[32m================= Your 30 day trial period has expired =======================\e[0m"
fi