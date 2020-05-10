import glob
import librosa
import numpy as np
import os

from sklearn.preprocessing import LabelBinarizer
import torch
from torch.utils.data.dataloader import DataLoader
from torch.utils.data.dataset import Dataset

from preprocess import (FEATURE_DIM, FFTSIZE, FRAMES, SAMPLE_RATE,
                        world_features)
from utility import Normalizer, speakers
from random import choice

class AudioDataset(Dataset):
    def __init__(self, data_dir: str):
        super(AudioDataset, self).__init__()
        self.data_dir = data_dir
        self.files = librosa.util.find_files(data_dir, ext='npy')
        self.encoder = LabelBinarizer().fit(speakers)

    def __getitem__(self, idx):
        p = self.files[idx]
        filename = os.path.basename(p)
        speaker = filename.split(sep='_', maxsplit=1)[0]
        label = self.encoder.transform([speaker])[0]
        mcep = np.load(p)
        mcep = torch.FloatTensor(mcep)
        mcep = torch.unsqueeze(mcep, 0)
        return mcep, torch.tensor(speakers.index(speaker), dtype=torch.long), torch.FloatTensor(label)

    def speaker_encoder(self):
        return self.encoder

    def __len__(self):
        return len(self.files)

def data_loader(data_dir: str, batch_size=4, shuffle=True, mode='train', num_workers=2):
    dataset = AudioDataset(data_dir)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, num_workers=num_workers)
    
    return loader

class TestSet(object):
    def __init__(self, data_dir: str):
        super(TestSet, self).__init__()
        self.data_dir = data_dir
        self.norm = Normalizer()
        
    def choose(self):
        r = choice(speakers)
        return r
    
    def test_data(self, src_speaker=None):
        if src_speaker:
            r_s = src_speaker
        else:
            r_s = self.choose()
            
        p = os.path.join(self.data_dir, r_s)
        wavfiles = librosa.util.find_files(p, ext='wav')
       
        res = {}
        for f in wavfiles:
            filename = os.path.basename(f)
            wav, _ = librosa.load(f, sr=SAMPLE_RATE, dtype=np.float64)
            f0, timeaxis, sp, ap, coded_sp = world_features(wav, SAMPLE_RATE, FFTSIZE, FEATURE_DIM)
            coded_sp_norm = self.norm.forward_process(coded_sp.T, r_s)

            if not res.__contains__(filename):
                res[filename] = {}
            res[filename]['coded_sp_norm'] = np.asarray(coded_sp_norm)
            res[filename]['f0'] = np.asarray(f0)
            res[filename]['ap'] = np.asarray(ap)
        return res, r_s    