import os
import sys
import logging

import math
import numpy as np
from threading import Thread
from multiprocessing import Process
from scipy.io.wavfile import read

from kaldi.matrix import Matrix, Vector, SubVector, DoubleVector
from kaldi.feat.mfcc import Mfcc, MfccOptions
from kaldi.feat.functions import compute_deltas, DeltaFeaturesOptions, sliding_window_cmn, SlidingWindowCmnOptions
from kaldi.ivector import compute_vad_energy, VadEnergyOptions, estimate_ivectors_online, \
        IvectorExtractor, IvectorExtractorUtteranceStats, IvectorEstimationOptions
from kaldi.gmm import DiagGmm, FullGmm
from kaldi.hmm.posterior import total_posterior
from kaldi.util.io import xopen


LOG = logging.getLogger(__name__)

def kaldi_Matrix(mat):
    _mat = Matrix(mat.num_rows, mat.num_cols)
    _mat.add_mat_(1, mat)
    return _mat

def make_feat_pipeline(base, sliding_opts,vad_opts, delta_opts=DeltaFeaturesOptions()):
    def feat_pipeline(vec, freq):
        feats = base.compute_features(vec, freq, 1.0)

        voice = Vector(compute_vad_energy(vad_opts, feats)) # Use origin mfcc to computed

        delta_feats = compute_deltas(delta_opts, feats)

        sliding_feats = Matrix(delta_feats.num_rows, delta_feats.num_cols)
        sliding_window_cmn(sliding_opts, delta_feats, sliding_feats)

        if not voice.sum():
            LOG.warning('No features were judged as voiced for utterance')
            return False

        dim = int(voice.sum())
        voice_feats = Matrix(dim, delta_feats.num_cols)
        feats = kaldi_Matrix(sliding_feats)
        
        index = 0
        for i, sub_vec in enumerate(feats):
            if voice[i] != 0 and voice[i] == 1:
                voice_feats.row(index).copy_row_from_mat_(feats, i)
                index += 1

        LOG.debug('Feats extract successed')
        return voice_feats

    return feat_pipeline

mfcc_opts = MfccOptions()
mfcc_opts.frame_opts.samp_freq = 16000
mfcc_opts.frame_opts.allow_downsample = True
mfcc_opts.mel_opts.num_bins = 40
mfcc_opts.num_ceps = 20
mfcc_opts.use_energy = True
mfcc = Mfcc(mfcc_opts)

sliding_opts = SlidingWindowCmnOptions()
sliding_opts.cmn_window = 300
sliding_opts.normalize_variance = False
sliding_opts.center = True

vad_opts = VadEnergyOptions()
vad_opts.vad_energy_threshold = 5.5
vad_opts.vad_energy_mean_scale = 0.5

delta_opts = DeltaFeaturesOptions()
delta_opts.window = 3
delta_opts.order = 2


feat_pipeline = make_feat_pipeline(mfcc, sliding_opts,vad_opts, delta_opts)


try:
    LOG.info('Loading ubm...')
    if not os.path.exists('app/extractor/final.ubm'):
        LOG.error('Not Found extractor/final.ubm, please recheck file')
        exit(1)
    with xopen('app/extractor/final.ubm') as ki:
        fgmm = FullGmm()
        fgmm.read(ki.stream(), ki.binary)
        gmm = DiagGmm()
        gmm.copy_from_full(fgmm)

    if not os.path.exists('app/extractor/final.ie'):
        LOG.error('Not Found app/extractor/final.ie, please recheck file')
        exit(1)

    with xopen('app/extractor/final.ie') as ki:
        extractor_ = IvectorExtractor()
        extractor_.read(ki.stream(), ki.binary)
        LOG.info('IvectorExtractor ready')


except Exception:
    raise Exception

LOG.info('Loading ubm model successed')

def make_gmm_pipeline(gmm, fgmm):
    def gmm_pipeline(feats, utt, min_post = 0.025):
        gselect = gmm.gaussian_selection_matrix(feats, 20)[1]
        num_frames = feats.num_rows
        utt_ok = True
        post = [ [] for i in range(num_frames) ]
        tot_loglike = 0
        for i in range(num_frames):
            frame = SubVector(feats.row(i))
            this_gselect = gselect[i]
            log_likes = Vector(fgmm.log_likelihoods_preselect(frame, this_gselect))
            tot_loglike += log_likes.apply_softmax_()
            if(abs(log_likes.sum()-1.0) > 0.01):
                utt_ok = False
            else:
                if min_post != 0:
                    max_index = log_likes.max_index()[1]
                    for x in range(log_likes.dim):
                        if log_likes[x] < min_post:
                            log_likes[x] = 0.0
                    if sum(log_likes) == 0:
                        log_likes[max_index] = 1.0
                    else:
                        log_likes.scale_(1.0/sum(log_likes))
            for x in range(log_likes.dim):
                if log_likes[x] != 0:
                    post[i].append((this_gselect[x], log_likes[x]))

        if not utt_ok:
            LOG.warning("Skipping utterance because bad posterior-sum encountered (NaN?)")
            return False
        else:
            LOG.debug('Like/frame for utt {} was {} perframe over {} frames.'.format(utt, tot_loglike/num_frames, num_frames))

        return post


    return gmm_pipeline

gmm_pipeline = make_gmm_pipeline(gmm, fgmm)

def scale_posterior(scale, post):
    if scale == 1.0:
        return post
    for i in range(len(post)):
        if scale == 0.0:
            post[i].clear()
        else:
            for x in range(len(post[i])):
                post[i][j][1] *= scale

    return post

tot_auxf_change = 0.0
tot_t = 0.0
need_2nd_order_stats = False

def make_ivector_pipeline(compute_objf_change = True, opts = IvectorEstimationOptions()):

    def ivector_pipeline(wav, utt=None):
        rate, vec = read(wav)
        vec = Vector(vec)
        feats = feat_pipeline(vec, rate)
        try:
            if utt is None:
                utt = os.path.basename(wav).split('.')[0]
        except Exception:
            utt = 'None'
        if not feats:
            return False
        post = gmm_pipeline(feats, utt)
        if not post:
            return False
        
        global tot_auxf_change
        global tot_t

        auxf = tot_auxf_change if compute_objf_change else None

        this_t = opts.acoustic_weight * total_posterior(post) 

        max_count_scale = 1.0
        if (opts.max_count > 0 and this_t > opts.max_count):
            max_count_scale = opts.max_count / this_t
            LOG.info("Scaling stats for utterance {} by scale {} due to --max-count={}".format(utt,max_count_scale, opts.max_count))
            this_t = opts.max_count

        post = scale_posterior(opts.acoustic_weight * max_count_scale, post) 

        utt_stats = IvectorExtractorUtteranceStats.new_with_params(extractor_.num_gauss(), extractor_.feat_dim(), need_2nd_order_stats)
        utt_stats.acc_stats(feats, post)

        ivector_ = DoubleVector()
        ivector_.resize_(extractor_.ivector_dim())
        ivector_[0] = extractor_.prior_offset()

        if auxf != None:
            old_auxf = extractor_.get_auxf(utt_stats, ivector_)
            extractor_.get_ivector_distribution(utt_stats, ivector_, None)
            new_auxf = extractor_.get_auxf(utt_stats, ivector_)
            auxf_change_ = new_auxf - old_auxf
        else:
            extractor_.get_ivector_distribution(utt_stats, ivector_, None)

        if auxf != None:
            T = total_posterior(post)
            tot_auxf_change += auxf_change_
            LOG.debug("Auxf change for utterance was {} per frame over {} frames (weighted)".format((auxf_change_/T), T))
        ivector_[0] -= extractor_.prior_offset()
        LOG.debug("Ivector norm for utterance {} was {}".format(utt ,ivector_.norm(2.0)))
        tot_t += this_t
        LOG.info("Ivector for utterance {} extract done".format(utt))
        return ivector_.numpy()


    return ivector_pipeline

ivector_pipeline = make_ivector_pipeline()


def thread_run(pair, num):
    # pair is (speaker, filename)
    _ivectors = []
    _spks = []
    for spk, filename in pair:
        _ivectors.append(ivector_pipeline(filename))
        _spks.append(spk)
    np.save('ivector/data_{}'.format(num), _ivectors)
    np.save('ivector/label_{}'.format(num), _spks)


if __name__ == '__main__':
    thread_num = 4
    pairs = [] 
    for speaker in os.listdir('waves'):
        for wav in os.listdir(os.path.join('waves', speaker)):
            if os.path.splitext(wav)[1] == '.wav':
                pairs.append((speaker ,os.path.join('waves', speaker, wav)))
    processes = []
    part = len(pairs) // thread_num
    for x in range(1, thread_num+1):
        if x == thread_num:
            _process = Process(target=thread_run, args=(pairs[(x-1)*part:], x))
        else: 
            _process = Process(target=thread_run, args=(pairs[(x-1)*part:x*part], x))
        processes.append(_process)
        _process.start()

    for x in processes:
        x.join()
    print("all done")

    ivectors = np.array([]).reshape(0,400)
    labels = []
    for x in range(1, thread_num+1):
        _ivector = np.load('ivector/data_{}.npy'.format(x))
        _label = np.load('ivector/label_{}.npy'.format(x))
        ivectors = np.concatenate([ivectors, _ivector])
        labels = np.concatenate([labels, _label])
    
    np.save('ivector/data', ivectors)
    np.save('ivector/label', labels)

