#1 = outmost folder (full path), 2 = first annotators name, 3 = second annotators name
cd $1/$2
for file in http*
do
# tmp=$(echo $file | sed 's/selim_/sumercan_/')
 python3 /home/osman/Dropbox/work/iaa-folia/justmerge.py -a $file $1/$3/$file
done
exit 0
