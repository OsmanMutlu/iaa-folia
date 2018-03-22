for file in batch/selim*
do
 tmp=$(echo $file | sed 's/selim_/sumercan_/')
 bash gethtmls.sh $file $tmp
done
python3 kappa_tags.py
exit 0
