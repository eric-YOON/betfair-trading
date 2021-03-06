from __future__ import print_function, division

from collections import defaultdict
import logging

import numpy as np
from numpy import array, sqrt, empty, argsort, zeros, ones, log, isnan, diag_indices_from, eye, dot, inf, linspace
from scipy import rand, randn
from scipy.stats import norm
from scipy.integrate import trapz

from trueskill import TrueSkill, Rating, rate


DEFAULT_MU = 0.0
DEFAULT_SIGMA = 8.0
DEFAULT_BETA = 4.0
DEFAULT_TAU = 0.1
DEFAULT_DRAW = 0.1


class HorseModel(object):
    def __init__(self, mu=DEFAULT_MU, sigma=DEFAULT_SIGMA, beta=DEFAULT_BETA,
                 tau=DEFAULT_TAU, draw_probability=DEFAULT_DRAW):
        """ mu - the initial mean of ratings
            sigma - the initial standard deviation of ratings
            beta - the distance that guarantees about an 80% chance of winning
            tau - the dynamic factor
            draw_probability - the draw probability of the game"""
        self._ts = TrueSkill(mu, sigma, beta, tau, draw_probability)
        self._ratings = self._create_ratings()

    def _create_ratings(self):
        return defaultdict(lambda: {'rating': (self._ts.create_rating(),),
                                    'n_races': 0,
                                    'n_wins': 0})

    def get_params(self):
        return {'mu': self._ts.mu,
                'sigma': self._ts.sigma,
                'beta': self._ts.beta,
                'tau': self._ts.tau,
                'draw_probability': self._ts.draw_probability}

    def fit_race(self, race):
        runners = race['selection']
        rating_groups = [self._ratings[r]['rating'] for r in runners]
        new_ratings = self._ts.rate(rating_groups, race['ranking'])

        for i, runner in enumerate(runners):
            horse = self._ratings[runner]
            horse['rating'] = new_ratings[i]
            horse['n_races'] += 1
            if runner in race['winners']:
                horse['n_wins'] += 1

    def fit(self, sorted_races, log_incremental=None):
        ratings = self._ratings
        stats = {'n_races': 0}

        for (i, race) in enumerate(sorted_races):
            runners = list(race['selection'])
            if len(runners) < 2:
                continue
            stats['n_races'] += 1
            rating_groups = [ratings[r]['rating'] for r in runners]
            new_ratings = self._ts.rate(rating_groups, race['ranking'])

            # assert len(new_ratings) == len(runners)
            diff = []
            for i, runner in enumerate(runners):
                horse = ratings[runner]
                horse['rating'] = new_ratings[i]
                horse['n_races'] += 1
                if runner in race['winners']:
                    horse['n_wins'] += 1
                if log_incremental is not None:
                    diff.append((runner, horse))

            if log_incremental is not None:
                log_incremental(race, dict(diff))

            if i % 100 == 0:
                logging.info('HorseModel.fit: %d races done' % i)

        stats['n_runners'] = len(ratings)
        return stats

    def pwin_mc(self, runners, nwins=1, prior_for_unobs=True):
        assert prior_for_unobs
        N = 1000
        R = empty((len(runners), N))
        for i, r in enumerate(self.get_ratings(runners)):
            R[i, :] = randn(N) * r.sigma + r.mu

        for i in xrange(N):
            ar = argsort(-array(R[:, i])).tolist()
            R[:, i] = [ar.index(x) for x in range(len(ar))]
        return np.sum(R < nwins, 1) / float(N)

    def pwin_trapz(self, runners):
        ratings = self.get_ratings(runners)
        N = len(ratings)
        mus = array(map(lambda x: x.mu, ratings))
        sigmas = array(map(lambda x: x.sigma, ratings))

        pwin = empty(N)
        start, end, nsteps = min(mus) - 3 * max(sigmas), max(mus) + 3 * max(sigmas), 5000

        us, p = linspace(start, end, nsteps), empty(nsteps)
        cdfs = [norm.cdf(us, loc=mus[i], scale=sigmas[i]) for i in xrange(N)]
        for i in xrange(N):
            p.fill(1.0)
            for j in xrange(N):
                if i == j:
                    p *= norm.pdf(us, loc=mus[j], scale=sigmas[j])
                else:
                    p *= cdfs[j]
            pwin[i] = trapz(p, dx=(end - start) / float(nsteps))
        return pwin

    def get_ratings(self, runners):
        return [self._ratings[x]['rating'][0] for x in runners]

    def get_runs(self, runners):
        return array([self._ratings[x]['n_races'] for x in runners])

    def to_dict(self):
        items = self._ratings.items()
        ratings = map(lambda x: {'runner': x[0],
                                 'mu': x[1]['rating'][0].mu,
                                 'sigma': x[1]['rating'][0].sigma,
                                 'n_races': x[1]['n_races'],
                                 'n_wins': x[1]['n_wins']}, items)
        return {
            'ts': {
                'mu': self._ts.mu,
                'sigma': self._ts.sigma,
                'beta': self._ts.beta,
                'tau': self._ts.tau,
                'draw_probability': self._ts.draw_probability
            },
            'ratings': ratings
        }

    @staticmethod
    def from_dict(hm_dict):
        hm = HorseModel(**hm_dict['ts'])
        for r in hm_dict['ratings']:
            hm._ratings[r['runner']] = {'rating': (Rating(r['mu'], r['sigma']), ),
                                        'n_races': r['n_races'],
                                        'n_wins': r['n_wins']}
        return hm


def get_implied_from_odds(odds):
    p = 1.0 / odds
    return p / np.sum(p)


# p = np.r_[.1, .6, .3]
# q = np.r_[.1, .5, .4]
#
# rm = RiskModel2(p, q)
# print(rm.optimal_w())
