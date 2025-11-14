# pitchclass_tonalstructures

This is a pytorch code repository accompanying the following paper:  

> Christof Weiß and Meinard Müller
> _From Music Scores to Audio Recordings: Deep Pitch-Class Representations for Measuring Tonal Structures_  
>  ACM Journal on Computing and Cultural Heritage, 2024

This repository only contains exemplary code and pre-trained models for some of the paper's experiments as well as some individual examples. All datasets used in the paper are publicly available (at least partially), especially our main dataset:
* [Wagner Ring Dataset (WRD)](https://zenodo.org/record/5139893)

For details and references, please see the paper.

## Feature extraction and prediction (Jupyter notebooks)

In this top folder, three Jupyter notebooks demonstrate how to 
* preprocess audio files for running our models (_01_precompute_features_),
* load a pretrained model for predicting pitches (_02_predict_with_pretrained_model_),
