scripts_loc=~/Experiments/Self_Regulation_Ontology_fMRI/fmri_analysis/scripts
data_loc=$HOME/tmp/fmri/data/
output=$HOME/tmp/fmri/output
docker run --rm  \
--mount type=bind,src=$scripts_loc,dst=/scripts \
--mount type=bind,src=$data_loc,dst=/data,readonly \
--mount type=bind,src=$output,dst=/output \
-ti fmri_env \
python task_analysis.py /output /Data --participant s358 --tasks stopSignal 

# as notebook
scripts_loc=~/Experiments/Self_Regulation_Ontology_fMRI/fmri_analysis/scripts
data_loc=$HOME/tmp/fmri/example_data
output=$HOME/tmp/fmri/output
docker run --rm  \
--mount type=bind,src=$scripts_loc,dst=/scripts \
--mount type=bind,src=$data_loc,dst=/data \
--mount type=bind,src=$output,dst=/output \
-ti -p 8888:8888 fmri_env \