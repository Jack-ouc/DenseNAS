import os
import logging
import shutil
import time

import numpy as np
import torch
import torch.nn as nn
from torch.autograd import Variable


class AvgrageMeter(object):

    def __init__(self):
        self.reset()

    def reset(self):
        self.avg = 0
        self.sum = 0
        self.cnt = 0

    def update(self, val, n=1):
        self.cur = val
        self.sum += val * n
        self.cnt += n
        self.avg = self.sum / self.cnt


def accuracy(output, target, topk=(1, 5)):
    maxk = max(topk)
    batch_size = target.size(0)

    _, pred = output.topk(maxk, 1, True, True)
    pred = pred.t()
    correct = pred.eq(target.view(1, -1).expand_as(pred))

    res = []
    for k in topk:
        correct_k = correct[:k].view(-1).float().sum(0)
        res.append(correct_k.mul_(100.0/batch_size))
    return res


def count_parameters_in_MB(model):
    return np.sum(np.prod(v.size()) for name, v in model.named_parameters() if "aux" not in name)/1e6


def save_checkpoint(state, is_best, save):
    filename = os.path.join(save, 'checkpoint.pth.tar')
    torch.save(state, filename)
    if is_best:
        best_filename = os.path.join(save, 'model_best.pth.tar')
        shutil.copyfile(filename, best_filename)


def save(model, model_path):
    torch.save(model.state_dict(), model_path)


def load_net_config(path):
    with open(path, 'r') as f:
        return f.readline()


def load_model(model, model_path):
    logging.info('Start loading the model from ' + model_path)
    model.load_state_dict(torch.load(model_path))
    logging.info('Loading the model finished!')


def drop_path(x, drop_prob):
    if drop_prob > 0.:
        keep_prob = 1.-drop_prob
        mask = Variable(torch.cuda.FloatTensor(x.size(0), 1, 1, 1).bernoulli_(keep_prob))
        x.div_(keep_prob)
        x.mul_(mask)
    return x


def create_exp_dir(path):
    if not os.path.exists(path):
        os.mkdir(path)
    print('Experiment dir : {}'.format(path))


def prod_sample(weights, sample_num):
    sampled_indices = []
    
    for j in range(sample_num):
        while 1:
            sample_factor = np.random.rand()
            for k in range(len(weights)):
                if sample_factor >= torch.sum(weights[0:k]) and \
                    sample_factor < torch.sum(weights[0:k+1]):
                    sampled_id = k
                    break
                else:
                    continue
            if sampled_id not in sampled_indices:
                sampled_indices.append(sampled_id)
                break
            else:
                continue

    return sampled_indices


def cross_entropy_with_label_smoothing(pred, target, label_smoothing=0.):
    logsoftmax = nn.LogSoftmax().cuda()
    n_classes = pred.size(1)
    # convert to one-hot
    target = torch.unsqueeze(target, 1)
    soft_target = torch.zeros_like(pred)
    soft_target.scatter_(1, target, 1)
    # label smoothing
    soft_target = soft_target * (1 - label_smoothing) + label_smoothing / n_classes
    return torch.mean(torch.sum(- soft_target * logsoftmax(pred), 1))


def latency_measure(module, input_size, batch_size, meas_times, mode='gpu'):
    assert mode in ['gpu', 'cpu']
    
    latency = []
    module.eval()
    input_size = (batch_size,) + tuple(input_size)    
    input_data = torch.randn(input_size)
    if mode=='gpu':
        input_data = input_data.cuda()

    for i in range(meas_times):
        with torch.no_grad():
            start = time.time()
            _ = module(input_data)
            if i >= 100:
                latency.append(time.time() - start)
    print(np.mean(latency) * 1e3, 'ms')
    return np.mean(latency) * 1e3


def latency_measure_fw(module, input_data, meas_times):
    latency = []
    module.eval()
    
    for i in range(meas_times):
        with torch.no_grad():
            start = time.time()
            output_data = module(input_data)
            if i >= 100:
                latency.append(time.time() - start)

    print(np.mean(latency) * 1e3, 'ms')
    return np.mean(latency) * 1e3, output_data

