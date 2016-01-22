#!/usr/bin/env python
# encoding: utf-8
"""
.. module:: visualize_wealth.analyze.py

.. moduleauthor:: Benjamin M. Gross <benjaminMgross@gmail.com>

"""
import collections
import numpy
import pandas
import scipy.stats
from .utils import zipped_time_chunks

def active_return(series, benchmark, freq = 'daily'):
    """
    Active returns is the geometric difference between annualized  
    returns

    :ARGS:

        series: ``pandas.Series`` of prices of the portfolio

        benchmark: ``pandas.Series`` of prices of the benchmark

    :RETURNS: 

        ``pandas.Series`` of active returns

    .. note:: Compound Linear Returns

        Linear returns are not simply subtracted, but rather the 
        compound difference is taken such that

        .. math::

            r_a = \\frac{1 + r_p}{1 + r_b} - 1
    """
    def _active_return(series, benchmark, freq = freq):
        port_ret = annualized_return(series, freq = freq)
        bench_ret = annualized_return(benchmark, freq = freq)

        return geometric_difference(port_ret, bench_ret)

    if isinstance(benchmark, pandas.DataFrame):
        return benchmark.apply(lambda x: _active_return(series, x, freq = freq))
    else:
        return _active_return(series, benchmark, freq = freq)

def active_returns(series, benchmark):
    """
    Active returns is defined as the compound difference between linear 
    returns

    :ARGS:

        series: ``pandas.Series`` of prices of the portfolio

        benchmark: ``pandas.Series`` of prices of the benchmark

    :RETURNS: 

        ``pandas.Series`` of active returns

    .. note:: Compound Linear Returns

        Linear returns are not simply subtracted, but rather the 
        compound difference is taken such that

        .. math::

            r_a = \\frac{1 + r_p}{1 + r_b} - 1
    """
    def _active_returns(series, benchmark):
        return (1 + linear_returns(series)).div(
            1 + linear_returns(benchmark)) - 1 

    if isinstance(benchmark, pandas.DataFrame):
        return benchmark.apply(lambda x: _active_returns(series, x))
    else:
        return _active_returns(series, benchmark)


def alpha(series, benchmark, freq = 'daily', rfr = 0.0):
    """
    Alpha is defined as excess return, over and above its 
    expected return, derived from an asset's sensitivity to an given benchmark, 
    and the return of that benchmrk.

    series: :class:`pandas.Series` or `pandas.DataFrame` of asset prices

    benchamrk: :class:`pandas.Series` of prices

    freq: :class:`string` either ['daily' , 'monthly', 'quarterly', or yearly']
    indicating the frequency of the data. Default, 'daily'

    rfr: :class:`float` of the risk free rate

    .. math::

        \\alpha \\triangleq (R_p - r_f) - \\beta_i \\cdot ( R_b - rf ) 
        
        \\textrm{where},

            R_p &= \\textrm{Portfolio Annualized Return} \\\\
            R_b &= \\textrm{Benchmark Annualized Return} \\\\
            r_f &= \\textrm{Risk Free Rate} \\\\
            \\beta &= \\textrm{Portfolio Sensitivity to the Benchmark}
    """
    def _alpha(series, benchmark, freq = 'daily', rfr = rfr):
        R_p = annualized_return(series, freq = freq)
        R_b = annualized_return(benchmark, freq = freq)
        b = beta(series, benchmark)
        return  R_p - rfr - b * (R_b - rfr)

    if isinstance(benchmark, pandas.DataFrame):
        return benchmark.apply(lambda x: _alpha(
            series, x, freq = freq, rfr = rfr))
    else:
        return _alpha(series, benchmark, freq = freq, rfr = rfr)



def annualized_return(series, freq = 'daily'):
    """
    Returns the annualized linear return of a series, i.e. the linear 
    compounding rate that would have been necessary, given the initial 
    investment, to arrive at the final value

    :ARGS:
    
        series: ``pandas.Series`` of prices
        
        freq: ``str`` of either ``daily, monthly, quarterly, or yearly``
        indicating the frequency of the data ``default=`` daily

    :RETURNS:
    
        ``float``: of the annualized linear return

    .. code:: python

        import visualize_wealth.performance as vwp

        linear_return = vwp.annualized_return(price_series, 
            frequency = 'monthly')
    
    """
    def _annualized_return(series, freq = 'daily'):

        fac = _interval_to_factor(freq)
        T = len(series) - 1.
        yr_frac = (series.index[-1] - series.index[0]).days / 365.
        if yr_frac > 1.:
            return numpy.exp(numpy.log(series[-1]/series[0]) * fac / T) - 1.
        else:
            return numpy.exp(numpy.log(series[-1]/series[0]) ) - 1.

    if isinstance(series, pandas.DataFrame):
        return series.apply(lambda x: _annualized_return(x, freq = freq))
    else:
        return _annualized_return(series, freq = freq)

def annualized_vol(series, freq = 'daily'):
    """
    Returns the annlualized volatility of the log changes of the price 
    series, by calculating the volatility of the series, and then 
    applying the square root of time rule

    :ARGS:
    
        series: ``pandas.Series`` of prices

        freq: ``str`` of either ``daily, monthly, quarterly, or yearly``    
        indicating the frequency of the data ``default=`` daily

    :RETURNS:
    
        float: of the annualized volatility

    .. note:: Applying the Square root of time rule


        .. math::

            \\sigma = \\sigma_t \\cdot \\sqrt{k},\\: \\textrm{where},

            k &= \\textrm{Factor of annualization} \\\\
            \\sigma_t &= \\textrm{volatility of period log returns}
        
    .. code::

        import visualize_wealth.performance as vwp

        ann_vol = vwp.annualized_vol(price_series, 
            frequency = 'monthly')
    """
    def _annualized_vol(series, freq = 'daily'):
        fac = _interval_to_factor(freq)
        series_rets = log_returns(series)
        return series_rets.std()*numpy.sqrt(fac)

    if isinstance(series, pandas.DataFrame):
        return series.apply(lambda x: _annualized_vol(x, freq = freq))
    else:
        return _annualized_vol(series, freq = freq)

def appraisal_ratio(series, benchmark, freq = 'daily', rfr = 0.):
    """
     A measure of the risk-adjusted return of a financial security or portfolio
     that is equal to the alpha, divided by the standard error between the 
     portfolio and the benchmark

    series: :class:`pandas.Series` or `pandas.DataFrame` of asset prices

    benchamrk: :class:`pandas.Series` of prices

    freq: :class:`string` either ['daily' , 'monthly', 'quarterly', or yearly']
    indicating the frequency of the data. Default, 'daily'

    rfr: :class:`float` of the risk free rate

    .. math:: 

        \\textrm{AR} \\triangleq \\frac{\\alpha}{\\epsilon} \\\\
        \\textrm{where,} \\\\
        \\alpha &= \\alpha \\textrm{, the risk adjused excess return} \\\\
        \\epsilon &= \\textrm{standard error, or idiosyncratic risk} \\\\

    """

    def _appraisal_ratio(series, benchmark, freq = freq, rfr = rfr):
        a = alpha(series, benchmark, freq = freq,  rfr = rfr)
        e = idiosyncratic_risk(series, benchmark ,freq = freq)
        return a / e

    if isinstance(benchmark, pandas.DataFrame):
        return benchmark.apply(lambda x: _appraisal_ratio(series, x, 
                                                          freq = freq,
                                                          rfr = rfr)
    )

    else:
        return _appraisal_ratio(series, benchmark, freq = freq, rfr = rfr)


def attribution_weights(series, factor_df):
    """
    Given a price series and explanatory factors factor_df, determine
    the weights of attribution to each factor or asset

    :ARGS:

        series: :class:`pandas.Series` of asset prices to explain given
        the factors or sub_classes in factor_df

        factor_df: :class:`pandas.DataFrame` of the prices of the
        factors or sub_classes to to which the asset prices can be
        attributed

    :RETURNS:

        given an optimal solution, a :class:`pandas.Series` of asset
        factor weights (summing to one) which best explain the
        series.  If an optimal solution is not found, None type is
        returned (with accompanying message)
    """
    def obj_fun(weights):
        tol = 1.e-5
        est = factor_df.apply(lambda x: numpy.multiply(weights, x),
                              axis = 1).sum(axis = 1)
        n = len(series)
        
        #when a variable is "excluded" reduce p for higher adj-r2
        p = len(weights[weights > tol])
        rsq = r2(series = series, benchmark = est)
        adj_rsq = 1 - (1 - rsq)*(n - 1)/(n - p - 1)
        return -1.*adj_rsq

    #linear returns
    series = linear_returns(series).dropna()

    #if isinstance(series, pandas.DataFrame) & len(series.columns == 1):
        #it's an n x 1 dataframe with a valid result
        #series = series[series.columns[0]]

    factor_df = linear_returns(factor_df).dropna()
    guess = numpy.random.rand(factor_df.shape[1])
    guess = pandas.Series(guess/guess.sum(), index = factor_df.columns)
    bounds = [(0., 1.) for i in numpy.arange(len(guess))]

    opt_fun = scipy.optimize.minimize(fun = obj_fun, 
                                      x0 = guess,
                                      bounds = bounds
    )
    opt_wts = pandas.Series(opt_fun.x, index = guess.index)
    opt_wts = opt_wts.div(opt_wts.sum())
    return opt_wts

def attribution_weights_by_interval(series, factor_df, interval):
    """
    Given a price series and explanatory factors factor_df, determine
    the weights of attribution to each factor or asset over differently 
    spaced time intervals

    :ARGS:

        series: :class:`pandas.Series` of asset prices to explain given
        the factors or sub_classes in factor_df

        factor_df: :class:`pandas.DataFrame` of the prices of the
        factors or sub_classes to to which the asset prices can be
        attributed

        interval: interval of the amount of time 

    :RETURNS:

        given an optimal solution, a :class:`pandas.DataFrame` of asset
        factor weights (summing to one) for each interval.  If an optimal 
        solution is not found, None type is returned (with accompanying 
        message)

    """
    chunks = zipped_time_chunks(series.index, interval)
    wt_dict = {}
    for beg, fin in chunks:
        wt_dict[beg] = attribution_weights(series[beg: fin], 
                                           factor_df.loc[beg: fin, :]
        )

    return pandas.DataFrame(wt_dict).transpose()
    
def beta(series, benchmark):
    """
    Returns the sensitivity of one price series to a chosen benchmark:

    :ARGS:

        series: ``pandas.Series`` of prices

        benchmark: :class:`Series` or :class:`DataFrame` of prices 
        of a benchmark to calculate the sensitivity against

    :RETURNS:

        float: the sensitivity of the series to the benchmark

    .. note:: Calculating Beta

        
        .. math::

           \\beta \\triangleq \\frac{\\sigma_{s, b}}{\\sigma^2_{b}},
           \\: \\textrm{where},

           \\sigma^2_{b} &= \\textrm{Variance of the Benchmark} \\\\
           \\sigma_{s, b} &= \\textrm{Covariance of the Series & Benchmark}
    
    """
    def _beta(series, benchmark):
        series_rets = log_returns(series)
        bench_rets = log_returns(benchmark)
        return numpy.divide(bench_rets.cov(series_rets), 
                            bench_rets.var())

    if isinstance(benchmark, pandas.DataFrame):
        return benchmark.apply(lambda x: _beta(series, x))
    else:
        return _beta(series, benchmark)

def beta_ew(series, benchmark, theta = 0.94):
    """
    Returns the exponentially weighted sensitivity of one return 
    series to a chosen benchmark

    :ARGS:

        series: :class:`Series` of prices

        benchmark: :class:`Series` of a benchmark to calculate the 
        sensitivity

        theta: :class:`float` of the exponential smoothing constant
        default to 0.94 MSCI Barra's ew constant

    :RETURNS:

        float: the sensitivity of the series to the benchmark

    """
    span = (1. + theta) / (1. - theta)
    series_rets = log_returns(series)
    bench_rets = log_returns(benchmark)
    
    cov = pandas.ewmcov(series_rets, 
                        bench_rets,
                        span = span,
                        min_periods = span
    )
    
    var = pandas.ewmvar(bench_rets, 
                        span = span, 
                        min_periods = span
    )
    
    return cov.div(var)


def consecutive(int_series):
    """
    Array logic (no for loops) and fast method to determine the number of
    consecutive ones given a `pandas.Series` of integers Derived from 
    `Stack Overflow
    <http://stackoverflow.com/questions/18196811/cumsum-reset-at-nan>`_

    :ARGS:

        int_series: :class:`pandas.Series` of integers as 0s or 1s

    :RETURNS:

        :class:`pandas.Series` of the consecutive ones
    """
    n = int_series == 0
    a = ~n
    c = a.cumsum()
    index = c[n].index
    d = pandas.Series(numpy.diff(numpy.hstack(( [0.], c[n] ))) , 
                      index =index)
    int_series[n] = -d
    return int_series.cumsum()

def consecutive_downtick_performance(series, n_ticks = 3):
    """
    Returns a two column :class:`pandas.DataFrame` with columns 
    `['performance','num_downticks']` that shows the cumulative 
    performance (in log returns) and the `num_upticks` number of 
    days the downtick lasted

    :ARGS:

        series: :class:`pandas.Series` of asset prices

    :RETURNS:

        :class:`pandas.DataFrame` of ``['performance','num_upticks']``.
        Performance is in log returns and `num_downticks` the number 
        of consecutive downticks for which the performance was 
        generated
    """
    def _consecutive_downtick_performance(series, n_ticks):
        dnticks = consecutive_downticks(series, n_ticks = n_ticks)
        series_dn = series[dnticks.index]
        st, fin = dnticks == 0, (dnticks == 0).shift(-1).fillna(True)
        n_per = dnticks[fin]
        series_rets = numpy.log(numpy.divide(series_dn[fin], 
                                             series_dn[st]))

        return pandas.DataFrame({'num_downticks':n_per,
                                 series.name: series_rets})
    
    if isinstance(series, pandas.DataFrame):
        return series.apply(lambda x: _consecutive_downtick_performance(
            x, n_ticks = n_ticks))
    else:
        return _consecutive_downtick_performance(series = series,
            n_ticks = n_ticks)
    
def consecutive_downtick_relative_performance(series, benchmark, n_ticks = 3):
    """
    Returns a two column :class:`pandas.DataFrame` with columns 
    `['outperformance','num_downticks']` that shows the cumulative 
    outperformance (in log returns) and the `num_upticks` number of 
    days the downtick lasted

    :ARGS:

        series: :class:`pandas.Series` of asset prices

        benchmark: :class:`pandas.Series` of prices to compare 
        ``series`` against

    :RETURNS:

        :class:`pandas.DataFrame` of ``['outperformance','num_upticks']``.
        Outperformance is in log returns and `num_downticks` the number 
        of consecutive downticks for which the outperformance was 
        generated
    """
    def _consecutive_downtick_relative_performance(series, benchmark, n_ticks):
        dnticks = consecutive_downticks(benchmark, n_ticks = n_ticks)
        series_dn = series[dnticks.index]
        bench_dn = benchmark[dnticks.index]
        st, fin = dnticks == 0, (dnticks == 0).shift(-1).fillna(True)
        n_per = dnticks[fin]
        series_rets = numpy.log(numpy.divide(series_dn[fin], 
                                             series_dn[st]))
        bench_rets = numpy.log(numpy.divide(bench_dn[fin], bench_dn[st]))
        return pandas.DataFrame({'outperformance':series_rets.subtract(
            bench_rets), 'num_downticks':n_per, series.name: series_rets,
            benchmark.name: bench_rets}, columns = [benchmark.name,
            series.name, 'outperformance', 'num_downticks'] )
    
    if isinstance(benchmark, pandas.DataFrame):
        return map(lambda x: _consecutive_downtick_relative_performance(
               series = series, benchmark = benchmark[x],n_ticks = n_ticks),
               benchmark.columns)
    else:
        return _consecutive_downtick_relative_performance(series = series,
               benchmark = benchmark, n_ticks = n_ticks)

def consecutive_downticks(series, n_ticks = 3):
    """
    Using the :func:`num_consecutive`, returns a :class:`pandas.Series` 
    of the consecutive downticks in the series greater than three 
    downticks

    :ARGS:

        series: :class:`pandas.Series` of the asset prices

    :RETURNS:

        :class:`pandas.Series` of the consecutive downticks of the series
    """
    w = consecutive( (series < series.shift(1)).astype(int) )
    agg_ind = w[w > n_ticks - 1].index.union_many(
              map(lambda x: w[w.shift(-x) == n_ticks].index,
              numpy.arange(n_ticks + 1) ))

    return w[agg_ind]

def consecutive_uptick_relative_performance(series, benchmark, n_ticks = 3):
    """
    Returns a two column :class:`pandas.DataFrame` with columns 
    ``['outperformance', 'num_upticks']`` that shows the cumulative 
    outperformance (in log returns) and the ``num_upticks`` number of 
    days the uptick lasted

    :ARGS:

        series: :class:`pandas.Series` of asset prices

        benchmark: :class:`pandas.Series` of prices to compare 
        ``series`` against

    :RETURNS:

        :class:`pandas.DataFrame` of ``['outperformance',
        'num_upticks']``. Outperformance is in log returns and 
        num_upticks the number of consecutive upticks for which the 
        outperformance was generated
    """
    def _consecutive_uptick_relative_performance(series, benchmark, n_ticks):
        upticks = consecutive_upticks(benchmark, n_ticks = n_ticks)
        series_up  = series[upticks.index]
        bench_up = benchmark[upticks.index]
        st, fin = upticks == 0, (upticks == 0).shift(-1).fillna(True)
        n_per = upticks[fin]
        series_rets = numpy.log(numpy.divide(series_up[fin], 
                                             series_up[st]))
        bench_rets = numpy.log(numpy.divide(bench_up[fin], bench_up[st]))
        return pandas.DataFrame({'outperformance':series_rets.subtract(
            bench_rets), 'num_upticks':n_per, series.name: series_rets,
            benchmark.name: bench_rets}, columns = [benchmark.name,
            series.name, 'outperformance', 'num_upticks'] )

    if isinstance(benchmark, pandas.DataFrame):
        return map(lambda x: _consecutive_uptick_relative_performance(
               series = series, benchmark = benchmark[x], n_ticks = n_ticks),
               benchmark.columns)
    else:
        return _consecutive_uptick_relative_performance(
               series = series, benchmark = benchmark, n_ticks = n_ticks)

def consecutive_uptick_performance(series, n_ticks = 3):
    """
    Returns a two column :class:`pandas.DataFrame` with columns 
    ``['performance', 'num_upticks']`` that shows the cumulative 
    performance (in log returns) and the ``num_upticks`` number of 
    days the uptick lasted

    :ARGS:

        series: :class:`pandas.Series` of asset prices

    :RETURNS:

        :class:`pandas.DataFrame` of ``['outperformance',
        'num_upticks']``. Outperformance is in log returns and 
        num_upticks the number of consecutive upticks for which the 
        outperformance was generated
    """
    def _consecutive_uptick_performance(series, n_ticks):
        upticks = consecutive_upticks(series, n_ticks = n_ticks)
        series_up  = series[upticks.index]
        st, fin = upticks == 0, (upticks == 0).shift(-1).fillna(True)
        n_per = upticks[fin]
        series_rets = numpy.log(numpy.divide(series_up[fin], 
                                             series_up[st]))
        return pandas.DataFrame({'num_upticks':n_per,
            series.name: series_rets} )

    if isinstance(series, pandas.DataFrame):
        return series.apply(lambda x: _consecutive_uptick_performance(x,
            n_ticks = n_ticks))

    else:
        return _consecutive_uptick_performance(
               series = series, n_ticks = n_ticks)

def consecutive_upticks(series, n_ticks = 3):
    """
    Using the :func:`num_consecutive`, returns a :class:`pandas.Series` 
    of the consecutive upticks in the series with greater than 3 
    consecutive upticks

    :ARGS:

        series: :class:`pandas.Series` of the asset prices

    :RETURNS:

        :class:`pandas.Series` of the consecutive downticks of the series
    """
    w = consecutive( (series > series.shift(1)).astype(int) )
    agg_ind = w[w > n_ticks - 1].index.union_many(
              map(lambda x: w[w.shift(-x) == n_ticks].index,
              numpy.arange(n_ticks + 1) ))

    return w[agg_ind]

def cumulative_turnover(alloc_df, asset_wt_df):
    """
    Provided an allocation frame (i.e. the weights to which the portfolio 
    was rebalanced), and the historical asset weights,  return the 
    cumulative turnover, where turnover is defined below.  The first 
    period is excluded of the ``alloc_df`` is excluded as that represents 
    the initial investment

    :ARGS:

        alloc_df: :class:`pandas.DataFrame` of the the weighting allocation 
        that was provided to construct the portfolio

        asset_wt_df: :class:`pandas.DataFrame` of the actual historical 
        weights of each asset

    :RETURNS:

        cumulative turnover

    .. note:: Calcluating Turnover

    Let :math:`\\tau_j =` Single Period period turnover for period 
    :math:`j`, and assets :math:`i = 1,:2,:...:,n`, each whose respective 
    portfolio weight is represented by :math:`\\omega_i`.
    
    Then the single period :math:`j` turnover for all assets 
    :math:`1,..,n` can be calculated as:
    
    .. math::

        \\tau_j = \\frac{\\sum_{i=1}^n|\omega_i - \\omega_{i+1}|  }{2}
        
    """
    #the dates when the portfolio are the cause of turnover
    ind = alloc_df.index[1:]
    try:
        return 0.5*asset_wt_df.loc[ind, :].sub(
            asset_wt_df.shift(-1).loc[ind, :]).abs().sum(axis = 1).sum()

    #the rebalance might have dates past the earliest price
    except KeyError:
        loc = alloc_df.index.searchsorted(asset_wt_df.index[0])
        tmp = alloc_df.iloc[loc:, :]
        ind = tmp.index[1:]
        return 0.5*asset_wt_df.loc[ind, :].sub(
            asset_wt_df.shift(-1).loc[ind, :]).abs().sum(axis = 1).sum()

def cvar_cf(series, p = .01):
    """
    CVaR (Expected Shortfall), using the `Cornish Fisher Approximation 
    <http://en.wikipedia.org/wiki/Cornish%E2%80%93Fisher_expansion>`_

    :ARGS:

        series: :class:`pandas.Series` or :class:`pandas.DataFrame` 
        of the asset prices

        p: :class:`float` of the desired percentile, defaults to .01 
        or the 1% CVaR

    :RETURNS:

        :class:`float` or :class:`pandas.Series` of the CVaR
    
    """
    def _cvar_cf(series, p):
        ppf = scipy.stats.norm.ppf
        pdf = scipy.stats.norm.pdf
        series_rets = log_returns(series)
        mu, sigma = series_rets.mean(), series_rets.std()
        skew, kurt = series_rets.skew(), series_rets.kurtosis() - 3.
        
        f = lambda x, skew, kurt: x + skew/6.*(x**2 - 1) + kurt/24.* x * (
            x**2 - 3.) - skew**2/36. * x * (2. * x**2  - 5.)

        loss = f(x = 1/p*(pdf(ppf(p))), skew = skew, 
                 kurt = kurt) * sigma - mu
        return  numpy.exp(loss) - 1.

    if isinstance(series, pandas.DataFrame):
        return series.apply(lambda x: _cvar_cf(x, p = p))
    else:
        return _cvar_cf(series, p = p)

def cvar_contrib(wts, prices, alpha = .10, n_sims = 100000):
    """
    Calculate each asset's contribution to CVaR based on it's 
    ew volatility and correlation to other assets, and it's 
    current portfolio weight

    :ARGS:

        wts: :class:`Series` of current weights

        prices: :class:`DataFrame` of prices

        alpha: :class:`float` of the cvar parameter

        n_sims: :class:`int` the number of simulations

    :RETURNS:

        :class:`pandas.Series` of proportional contribution

    .. note:: alternative parameters

        currently the span (for exponentially weighted stats)
        and phi (for the degrees of freedom of the t-distribution)
        are not changeable for the function
    """
    
    def _spectral_fun(alpha, n_sims):
        
        th = numpy.ceil(alpha*n_sims) # threshold
        th = int(th) 
        spc = pandas.Series(
                  numpy.zeros([n_sims,])
        )
        
        spc[:th] = 1
        return spc/spc.sum()

    m, n = prices.shape

    rets = analyze.log_returns(prices)
    cov = pandas.ewmcov(rets, span = 21., min_periods = 21)
    zs = pandas.Series(numpy.zeros(n,), index = prices.columns)

    sims = mvt_rnd(mu = zs, 
                   covm = cov.iloc[-1, :, :],
                   phi = 3,
                   n_sim = n_sims
    )

    psi = sims.dot(wts)
    spec = _spectral_fun(alpha = alpha, 
                         n_sims = n_sims
    )

    srtd = psi.copy()
    ind = psi.argsort()
    srtd.sort()

    # pandas multiplies using indexes, so remove index 
    #cvar = srtd[ind].dot(spec.values)

    d = {}

    for asset in wts.index:
        d[asset] = sims.loc[ind, asset].dot(spec.values)

    acvar = pandas.Series(d)
    tmp = acvar.mul(wts)
    return tmp/tmp.sum()

def cvar_norm(series, p = .01):
    """
    CVaR (Conditional Value at Risk), fitting the normal distribution 
    to pthe historical time series using

    :ARGS:

        series: :class:`pandas.Series` or :class:`pandas.DataFrame` of 
        the asset prices
        
        p: :class:`float` of the desired percentile, defaults to .01 
        or the 1% CVaR

    :RETURNS:

        :class:`float` or :class:`pandas.Series` of the CVaR
    """
    def _cvar_norm(series, p):
        pdf = scipy.stats.norm.pdf
        series_rets = log_returns(series)
        mu, sigma = series_rets.mean(), series_rets.std()
        var = lambda alpha: scipy.stats.distributions.norm.ppf(1 - alpha)
        return numpy.exp(sigma/p * pdf(var(p)) - mu) - 1.

    if isinstance(series, pandas.DataFrame):
        return series.apply(lambda x: _cvar_norm(x, p = p))
    else:
        return _cvar_norm(series, p = p)

def cvar_np(series, p):
    """
    Non-parametric CVaR or Expected Shortfall, solely based on the 
    mean of historical values

    :ARGS:

        series: :class:`pandas.Series` or :class:`pandas.DataFrame` of 
        the asset prices

        p: :class:`float` of the desired percentile, defaults to .01 or 
        the 1% CVaR

    :RETURNS:

        :class:`float` or :class:`pandas.Series` of the CVaR
    
    """
    def _cvar_mu_np(series, p):
        series_rets = linear_returns(series)
        var = numpy.percentile(series_rets, p*100.)
        return  -series_rets[series_rets <= var].mean()

    if isinstance(series, pandas.DataFrame):
        return series.apply(lambda x: _cvar_mu_np(x, p = p))
    else:
        return _cvar_mu_np(series, p = p)

def downcapture(series, benchmark):
    """
    Returns the proportion of ``series``'s cumulative negative returns 
    to ``benchmark``'s cumulative  returns, given benchmark's returns 
    were negative in that period

    :ARGS:

        series: ``pandas.Series`` of prices

        benchmark: ``pandas.Series`` of prices to compare ``series`` 
        against

    :RETURNS:

        ``float`` of the downcapture of cumulative positive ret

    .. seealso:: :py:data:`median_downcapture(series, benchmark)`

    """
    def _downcapture(series, benchmark):
        series_rets = log_returns(series)
        bench_rets = log_returns(benchmark)
        index = bench_rets < 0.
        return series_rets[index].mean() / bench_rets[index].mean()

    if isinstance(benchmark, pandas.DataFrame):
        return benchmark.apply(lambda x: _downcapture(series, x))
    else:
        return _downcapture(series, benchmark)

def downside_deviation(series, freq = 'daily'):
    """
    Returns the volatility of the returns that are less than zero

    :ARGS:

        series:``pandas.Series`` of prices

        freq: ``str`` of frequency, either ``daily, monthly, quarterly, 
        or yearly``

    :RETURNS:

        float: of the downside standard deviation

    """
    def _downside_deviation(series, freq = 'daily'):
        fac = _interval_to_factor(freq)
        series_rets = log_returns(series)
        index = series_rets < 0.    
        return series_rets[index].std()*numpy.sqrt(fac)

    if isinstance(series, pandas.DataFrame):
        return series.apply(lambda x: _downside_deviation(x, freq = freq))
    else:
        return _downside_deviation(series, freq = freq)

def drawdown(series):
    """
    Returns a :class:`pandas.Series` or :class:`pandas.DataFrame` 
    (same as input) of the drawdown, i.e. distance from rolling 
    cumulative maximum.  Values are negative specifically to be used
    in plots

    :ARGS:
    
        series: :class:`pandas.Series` or :class:`pandas.DatFrame` of 
        prices

    :RETURNS:
    
        same type as input

    .. code::

        drawdown = vwp.drawdown(price_df)
        """

    def _drawdown(series):
        dd = (series/series.cummax() - 1.)
        dd[0] = numpy.nan
        return dd

    if isinstance(series, pandas.DataFrame):
        return series.apply(_drawdown)
    else:
        return _drawdown(series)

def ew_vol(series, theta = 0.94, freq = 'daily'):
    """
    Returns the exponentially weighted, annualized standard deviation

    :ARGS:

        series: :class:`Series` or :class:`DataFrame` of prices

        theta: coefficient of decay, default BARRA's value of .94 
        which roughly equates to a span of 33 days

        freq: :class:`string` of either ['daily', 'monthly', 'quarterly', 
        'yearly']
    """
    span = (1. + theta)/(1 - theta)

    log_rets = log_returns(series)

    fac = _interval_to_factor(freq)

    ew_vol = pandas.ewmstd(log_rets,
                           span = span,
                           min_periods = span
    )

    return ew_vol*numpy.sqrt(fac)
        

def geometric_difference(a, b):
    """
    Returns the geometric difference of returns where

    :ARGS:

        a: :class:`pandas.Series` or :class:`float`

        b: :class:`pandas.Series` or :class:`float`

    :RETURNS:

        same class as inputs

    .. math::

        \\textrm{GD} = \\frac{(1 + a )}{(1 + b)}  - 1 \\\\
    """
    if isinstance(a, pandas.Series):
        msg = "index must be equal for pandas.Series"
        assert a.index.equals(b.index), msg
        return (1. + a).divide(1. + b) - 1.
    else:
        return (1. + a) / (1. + b) - 1.

def idiosyncratic_as_proportion(series, benchmark, freq = 'daily'):
    """
    Returns the idiosyncratic risk as proportion of total volatility

    :ARGS:

        series: ``pandas.Series`` of prices

        benchmark: ``pandas.Series`` to compare ``series`` against

        freq: ``str`` of frequency, either ``daily, monthly, quarterly, 
        or yearly``

    :RETURNS:

        ``float`` between (0, 1) representing the proportion of  
        volatility represented by idiosycratic risk
        
    """
    def _idiosyncratic_as_proportion(series, benchmark, freq = 'daily'):
        fac = _interval_to_factor(freq)
        series_rets = log_returns(series)
        return idiosyncratic_risk(series, benchmark, freq)**2 / (
            annualized_vol(series, freq)**2)

    if isinstance(benchmark, pandas.DataFrame):
        return benchmark.apply(lambda x: _idiosyncratic_as_proportion(
            series, x, freq))
    else:
        return _idiosyncratic_as_proportion(series, benchmark, freq)

def idiosyncratic_risk(series, benchmark, freq = 'daily'):
    """
    Returns the idiosyncratic risk, i.e. unexplained variation between 
    a price series and a chosen benchmark 

    :ARGS:

       series: ``pandas.Series`` of prices

       benchmark: ``pandas.Series`` to compare ``series`` against

       freq: ``str`` of frequency, either ``daily, monthly, quarterly, 
       or yearly``

    :RETURNS:

        float: the idiosyncratic volatility (not variance)


    .. note:: Additivity of an asset's Variance

        An asset's variance can be broken down into systematic risk, 
        i.e. that proportion of risk that can be attributed to some 
        benchmark or risk factor and idiosyncratic risk, or the 
        unexplained variation between the series and the chosen 
        benchmark / factor.  

        Therefore, using the additivity of variances, we can calculate 
        idiosyncratic risk as follows:

       .. math::

           \\sigma^2_{\\textrm{total}} = \\sigma^2_{\\beta} + 
           \\sigma^2_{\\epsilon} + \\sigma^2_{\\epsilon, \\beta}, 
           \\: \\textrm{where}, 

           \\sigma^2_{\\beta} &= \\textrm{variance attributable to 
           systematic risk}
           \\\\
           \\sigma^2_{\\epsilon} &= \\textrm{idiosyncratic risk} \\\\
           \\sigma^2_{\\epsilon, \\beta} &= \\textrm{covariance 
           between idiosyncratic
           and systematic risk, which by definition} = 0 \\\\

           \\Rightarrow \\sigma_{\\epsilon} = \\sqrt{\\sigma^2_{\\beta} + 
           \\sigma^2_{\\epsilon, \\beta}}

    """
    def _idiosyncratic_risk(series, benchmark, freq = 'daily'):
        fac = _interval_to_factor(freq)
        series_rets =log_returns(series)
        bench_rets = log_returns(benchmark)
        series_vol = annualized_vol(series, freq)
        benchmark_vol = annualized_vol(benchmark, freq)
        return numpy.sqrt(series_vol**2 - beta(series, benchmark)**2 * (
            benchmark_vol ** 2))

    if isinstance(benchmark, pandas.DataFrame):
        return benchmark.apply(lambda x: _idiosyncratic_risk(
            series, x, freq = freq))
    else:
        return _idiosyncratic_risk(series, benchmark, freq)

def information_ratio(series, benchmark, freq = 'daily'):
    """
    A measure of the risk-adjusted return of a financial security or portfolio
    that is equal to the active return divided by the tracking error between the 
    portfolio and the benchmark (MATE is used here, see the benefits of 
        MATE over TE)

    series: :class:`pandas.Series` or `pandas.DataFrame` of asset prices

    benchamrk: :class:`pandas.Series` of prices

    freq: :class:`string` either ['daily' , 'monthly', 'quarterly', or yearly']
    indicating the frequency of the data. Default, 'daily'

    rfr: :class:`float` of the risk free rate

    .. note:: Calculating Information Ratio

        .. math:: 

            \\textrm{IR} \\triangleq \\frac{\\alpha}{\\omega} \\\\
        
        where,

        .. math::

            \\alpha &= \\textrm{active return} \\\\
            \\omega &= \\textrm{tracking error} \\\\

    """
    def _information_ratio(series, benchmark, freq = freq):
        ar = active_return(series, benchmark, freq = freq)
        mate = mean_absolute_tracking_error(series, benchmark, freq = freq)
        return ar / mate

    if isinstance(benchmark, pandas.DataFrame):
        return benchmark.apply(lambda x: _information_ratio(series, x, freq = freq))
    else:
        return _information_ratio(series, benchmark, freq = freq)

def jensens_alpha(series, benchmark, rfr = 0., freq = 'daily'):
    """
    Returns the `Jensen's Alpha 
    <http://en.wikipedia.org/wiki/Jensen's_alpha>`_ or the excess 
    return based on the systematic risk of the ``series`` relative to
    the ``benchmark``

    :ARGS:

        series: ``pandas.Series`` of prices 
        
        benchmark: ``pandas.Series`` of the prices to compare 
        ``series`` against

        rfr: ``float`` of the risk free rate

        freq: ``str`` of frequency, either daily, monthly, quarterly, 
        or yearly

    :RETURNS:

        ``float`` representing the Jensen's Alpha

    .. note:: Calculating Jensen's Alpha

        .. math::

            \\alpha_{\\textrm{Jensen}} = r_p - \\beta \\cdot r_b 
        
        Where,

        .. math::

            r_p &= \\textrm{annualized linear return of the portfolio} 
            \\\\
            \\beta &= \\frac{\\sigma_{s, b}}{\\sigma^2_{b}} \\\\
            r_b &= \\textrm{annualized linear return of the benchmark}

    """
    def _jensens_alpha(series, benchmark, rfr = 0., freq = 'daily'):
        fac = _interval_to_factor(freq)
        series_ret = annualized_return(series, freq)
        bench_ret = annualized_return(benchmark, freq)
        return series_ret - (rfr + beta(series, benchmark)*(
            bench_ret - rfr))

    if isinstance(benchmark, pandas.DataFrame):
        return benchmark.apply(lambda x: _jensens_alpha(
            series, x, rfr = rfr, freq = freq))
    else:
        return _jensens_alpha(series, benchmark, rfr = rfr, freq = freq)

def linear_returns(series):
    """
    Returns a series of linear returns given a series of prices
    
    :ARGS:

        series: ``pandas.Series`` of prices

    :RETURNS:

        series: ``pandas.Series`` of linear returns

    .. note:: Calculating Linear Returns

            .. math::

                R_t = \\frac{P_{t+1}}{P_t} - 1
             
    """
    def _linear_returns(series):
        return series.div(series.shift(1)) - 1
    if isinstance(series, pandas.DataFrame):
        return series.apply(_linear_returns)
    else:
        return _linear_returns(series)    

def log_returns(series):
    """
    Returns a series of log returns given a series of prices where

    :ARGS:

        series: ``pandas.Series`` of prices

    :RETURNS:

        series: ``pandas.Series`` of log returns 

    .. note:: Calculating Log Returns

        .. math::

            R_t = \\log(\\frac{P_{t+1}}{P_t})
         
    """
    def _log_returns(series):
        return series.apply(numpy.log).diff()
    if isinstance(series, pandas.DataFrame):
        return series.apply(_log_returns)
    else:
        return _log_returns(series)

def log_returns_chol_adj(frame, theta = 0.94):
    """
    Create volatility adjusted historical returns that preserve the
    covariance structure while providing scaled-appropriate returns
    to calculate tail-risk measures

    :ARGS:

        frame: :class:`DataFrame` of prices

        theta: :class:`float` of the decay parameter to use for the
        exponential smoothing

    :RETURNS:

        :class:`DataFrame` of vol adjusted log returns preserving the
        covariance structure

    .. note:: Calculation explanation

        The calculation comes from the Duffie & Pan 1997, where the 
        Cholesky matrix of covariance matrix is used in place of the
        square root of the variance, in the volatility adjustment, and
        can be seen in `Value at Risk Models <http://goo.gl/BZHsjR>`_, 
        by Carol Alexander  

        Where,

        .. math:: 

            \\tilde{\\mathbb{x}_t} = \\mathbb{Q}_T\\mathbb{Q}^{-1}_t
            \\mathbb{x}_t, \\; t = 1, 2, ..., T \\\\ \\\\
        
        Where

        .. math:: 

            \\tilde{\\mathbb{x}_t} &= \\textrm{ the stock returns } 
            \\textrm{adjusted to have constant covariance } \\\\
            \\mathbb{Q}_t &=
            \\textrm{ the Cholesky matrix of the covariance matrix } \\\\ 
            \\mathbb{x}_t &= \\textrm{ the unadjusted stock returns}
    """
    #define the truncated functions
    dot = numpy.dot
    inv = numpy.linalg.inv
    chol = numpy.linalg.cholesky

    span = (1. + theta)/(1 - theta)

    log_rets = log_returns(frame)

    ew_cov = pandas.ewmcov(log_rets, 
                           span = span,
                           min_periods = span
    )
    q_T = chol(ew_cov.iloc[-1, :, :])
    d = {}
    for row in ew_cov.dropna().items:
        q_t = chol(ew_cov.loc[row, :, :])
        d[row] = pandas.Series(dot(log_rets.xs(row),
                               dot(q_T, inv(q_t))),
                               index = log_rets.columns
        )

    new_logs = pandas.DataFrame(d).transpose()
    return new_logs.reindex(log_rets.index)



def log_returns_vol_adj(series, theta = 0.94, freq = 'daily'):
    """
    Returns the volatility scaled log returns

    :ARGS:

        series: :class:`Series` or :class:`DataFrame` of prices

        theta: :class:`float` of the decay parameter to use for the
        exponential smoothing for volatility

        freq: :class:`string` from ['daily', 'monthly', 
        'quarterly', 'yearly']

    :RETURNS:

        volatility scaled log returns of the same dtype provided

    .. note:: Calculating Vol Adjustment Factor

       .. math::

           \\tilde{r}_{t,T} = \\frac{\\sigma_T}{\\sigma_t}\\cdot r_{t}

       This methodology is most common in using scaled historical 
       returns to calculate VaR and CVaR

    """
    def _log_ret_vol_adj(series, theta, freq):
        log_rets = log_returns(series)
        vol = ew_vol(series, theta = theta, freq = freq)
        scale = vol[-1] / vol
        return log_rets.mul(scale)

    if isinstance(series, pandas.DataFrame):
        return series.apply(
            lambda x: _log_ret_vol_adj(x, theta = theta, freq = freq)
        )
    else:
        return _log_ret_vol_adj(series, theta = theta, freq = freq)

def max_drawdown(series):
    """
    Returns the maximum drawdown, or the maximum peak to trough linear 
    distance, as a positive drawdown value

    :ARGS:
    
        series: ``pandas.Series`` of prices

    :RETURNS:
    
        float: the maximum drawdown of the period, expressed as a 
        positive number

    .. code::

        import visualize_wealth.performance as vwp

        max_dd = vwp.max_drawdown(price_series)
        """
    def _max_drawdown(series):
        return numpy.max(1 - series/series.cummax())
    if isinstance(series, pandas.DataFrame):
        return series.apply(_max_drawdown)
    else:
        return _max_drawdown(series)

def mctr(asset_df, portfolio_series):
    """
    Return a :class:`pandas.Series` of the marginal contribution for 
    risk ("mctr") for each of the assets that construct ``portfolio_df``

    :ARGS:

        asset_df: :class:`pandas.DataFrame` of asset prices

        portfolio_series: :class:`pandas.Series` of the portfolio value 
        that is consructed by ``asset_df``

    :RETURNS:

        a :class:`pandas.Series` of each of the asset's marginal 
        contribution to risk

    .. note:: Calculating Marginal Contribution to Risk

        If we define, :math:`MCR_i` to be the Marginal Contribution to 
        Risk for asset :math:`i`, then,

        .. math::

            MCTR_i &= \\sigma_i \\cdot \\rho_{i, P} \\\\

        Where,

        .. math::
            
            \\sigma_i &= \\textrm{volatility of asset } i, \\\\
            \\rho_i &= \\textrm{correlation of asset } i
            \\textrm{ with the Portfolio}

    .. note:: Reference for Further Reading

        MSCI Barra did an extensive (and easy to read) white paper 
        entitled `Risk Contribution <http://bit.ly/1eGmxJG>`_ that 
        explicitly details the risk exposure calculation.
    """
    asset_rets = log_returns(asset_df)
    port_rets = log_returns(portfolio_series)
    return asset_rets.corrwith(port_rets).mul(asset_rets.std())

def mean_absolute_tracking_error(series, benchmark, freq = 'daily'):
    """
    Returns Carol Alexander's calculation for Mean Absolute Tracking 
    Error ("MATE").


    :ARGS:

        series: ``pandas.Series`` of prices

        benchmark: ``pandas.Series`` to compare ``series`` against

        freq: ``str`` of frequency, either ``daily, monthly, quarterly, 
        or yearly`` 


    :RETURNS:

        ``float`` of the mean absolute tracking error
        
    .. note:: Why Mean Absolute Tracking Error

        One of the downfalls of 
        `Tracking Error <http://en.wikipedia.org/wiki/Tracking_error>`_ 
        ("TE") is that diverging price series that diverge at a constant 
        rate **may** have low TE.  MATE addresses this issue.
        
        .. math::
    
           \\sqrt{\\frac{(T-1)}{T}\\cdot \\tau^2 + \\bar{R}} \\: 
           \\textrm{where}

           \\tau &= \\textrm{Tracking Error} \\\\
           \\bar{R} &= \\textrm{mean of the active returns}

    """
    def _mean_absolute_tracking_error(series, benchmark, freq = 'daily'):
        active_rets = active_returns(series = series, 
                                     benchmark = benchmark)
        N = active_rets.shape[0]
        return numpy.sqrt((N - 1)/float(N) * tracking_error(
            series, benchmark, freq)**2 + active_rets.mean()**2)

    if isinstance(benchmark, pandas.DataFrame):
        return benchmark.apply(lambda x: _mean_absolute_tracking_error(
            series, x, freq = freq))
    else:
        return _mean_absolute_tracking_error(series, benchmark, 
                                             freq = freq)

def median_downcapture(series, benchmark):
    """
    Returns the median downcapture of a ``series`` of prices against a 
    ``benchmark`` prices, given that the ``benchmark`` achieved negative 
    returns in a given period

    :ARGS:

        series: ``pandas.Series`` of prices

        benchmark: ``pandas.Series`` of prices to compare ``series`` 
        against

    :RETURNS:

        ``float`` of the median downcapture

    .. warning:: About Downcapture
        
        Downcapture can be a difficult statistic to ensure validity.  As 
        downcapture is :math:`\\frac{\\sum{r_{\\textrm{series}}}}
        {\\sum{r_{b|r_i \\geq 0}}}` or the median values (in this case), 
        dividing by small numbers can have asymptotic effects to the 
        overall value of this statistic.  Therefore, it's good to do a 
        "sanity check" between ``median_upcapture`` and ``upcapture``
    
    """
    def _median_downcapture(series, benchmark):
        series_rets = log_returns(series)
        bench_rets = log_returns(benchmark)
        index = bench_rets < 0.
        return series_rets[index].median() / bench_rets[index].median()

    if isinstance(benchmark, pandas.DataFrame):
        return benchmark.apply(lambda x: _median_downcapture(series, x))
    else:
        return _median_downcapture(series, benchmark)

def median_upcapture(series, benchmark):
    """
    Returns the median upcapture of a ``series`` of prices against a 
    ``benchmark`` prices, given that the ``benchmark`` achieved 
    positive returns in a given period

    :ARGS:

        series: ``pandas.Series`` of prices

        benchmark: ``pandas.Series`` of prices to compare ``series`` 
        against

    :RETURNS:

        float: of the median upcapture 

    .. warning:: About Upcapture

        Upcapture can be a difficult statistic to ensure validity.  As 
        upcapture is :math:`\\frac{\\sum{r_{\\textrm{series}}}}
        {\\sum{r_{b|r_i \\geq 0}}}` or the median values (in this case), 
        dividing by small numbers can have asymptotic effects to the 
        overall value of this statistic.  Therefore, it's good to do a 
        "sanity check" between ``median_upcapture`` and ``upcapture``
        
    """
    def _median_upcapture(series, benchmark):
        series_rets = log_returns(series)
        bench_rets = log_returns(benchmark)
        index = bench_rets > 0.
        return series_rets[index].median() / bench_rets[index].median()

    if isinstance(benchmark, pandas.DataFrame):
        return benchmark.apply(lambda x: _median_upcapture(series, x))
    else:
        return _median_upcapture(series, benchmark)

def mvt_rnd(mu, covm, phi, n_sim):
    """
    Create an repr(n_sim) simluation of a multi-variate t 
    distribution with repr(phi) degrees of freedom, mean repr(mu),
    and covariance structure repr(covm)
    
    :ARGS:

        mu: :class:`Series` of average returns

        covm: :class:`DataFrame` of the assets covariance matrix

        phi: :class:`float` of t-distribution degrees of freedom

        n_sim: :class:`int` of the number of simulations to make

    :RETURNS:

        :class:`DataFrame` dim in {n_sim, mu.shape} of simulations

    .. note::

        Transformation taken from `Kenny Chowdary's website
        <http://bit.ly/1Kh8gku>`_

    """
    d = len(covm)

    g = numpy.tile(numpy.random.gamma(phi/2., 2./phi, n_sim), (d, 1)).T
    Z = numpy.random.multivariate_normal(numpy.zeros(d), covm, n_sim)
    ret = mu.values + Z/numpy.sqrt(g)

    return pandas.DataFrame(ret, columns = mu.index)

def period_returns(series, freq = 'daily', interval = 'quarterly'):
    """
    Return the disjoint periodic returns of series at interval, given the 
    time frequency of the data in series is freq.

    :ARGS:

        series: :class:`pandas.Series` of prices

        freq: :class:`string` in ['daily', 'monthly', 'quarterly', 'yearly'] of 
        the frequency of the data

        interval: :class:`string` of the periodicity of the interval you wish to
        return, in ['monthly', 'quarterly', 'yearly']

    :RETURNS:

        :class:`pandas.Series`
    """
    def _period_returns(series, freq, interval):
        fmat = {'monthly': lambda x: '{0}-{1}'.format(x.month, x.year), 
                'quarterly': lambda x: 'q{0}-{1}'.format(x.quarter, x.year),
                'yearly': lambda x: x.year
                }

        chunks = zipped_time_chunks(series.index, interval)
        dt_l = []
        d = {}
        for beg, fin in chunks:
            key = fmat[interval](beg)
            d[key] = annualized_return(series[beg:fin], freq = freq)
            dt_l.append(key)

        return pandas.Series(d, index = dt_l)

    if isinstance(series, pandas.Series):
        return _period_returns(series = series, freq = freq, interval = interval)
    else:
        return series.apply(lambda x: _period_returns(series = x,
                                                      freq = freq,
                                                      interval = interval)
        )

def period_volatility(series, freq = 'daily', interval = 'quarterly'):
    """
    Return the disjoint periodic volatility of series at interval, given the 
    time frequency of the data in series is freq.

    :ARGS:

        series: :class:`pandas.Series` of prices

        freq: :class:`string` in ['daily', 'monthly', 'quarterly', 'yearly'] of 
        the frequency of the data

        interval: :class:`string` of the periodicity of the interval you wish to
        return, in ['monthly', 'quarterly', 'yearly']

    :RETURNS:

        :class:`pandas.Series`
    """
    def _period_volatility(series, freq, interval):
        fmat = {'monthly': lambda x: '{0}-{1}'.format(x.month, x.year), 
                'quarterly': lambda x: 'q{0}-{1}'.format(x.quarter, x.year),
                'yearly': lambda x: x.year
                }

        chunks = zipped_time_chunks(series.index, interval)

        dt_l = []
        d = {}
        for beg, fin in chunks:
            key = fmat[interval](beg)
            d[key] = annualized_vol(series[beg:fin], freq = freq)
            dt_l.append(key)

        return pandas.Series(d, index = dt_l)

    if isinstance(series, pandas.Series):
        return _period_volatility(series = series, freq = freq, interval = interval)
    else:
        return series.apply(lambda x: _period_volatility(series = x,
                                                         freq = freq,
                                                         interval = interval)
        )

def r2(series, benchmark):
    """
    Returns the R-Squared or `Coefficient of Determination
    <http://en.wikipedia.org/wiki/Coefficient_of_determination>`_ 
    for a univariate regression (does not adjust for more independent 
    variables)
    
    .. seealso:: :meth:`r2_adjusted`

    :ARGS:

        series: :class`pandas.Series` of of log returns

        benchmark: :class`pandas.Series` of log returns to regress 
        ``series`` against

    :RETURNS:

        float: of the coefficient of variation
    """
    def _r_squared(x, y):
        X = pandas.DataFrame({'ones': 1., 'xs': x})
        beta = numpy.linalg.inv(X.transpose().dot(X)).dot(
            X.transpose().dot(y) )
        y_est = beta[0] + beta[1]*x
        ss_res = ((y_est - y)**2).sum()
        ss_tot = ((y - y.mean())**2).sum()
        return 1 - ss_res/ss_tot


    if isinstance(benchmark, pandas.DataFrame):
        #remove the numpy.nan's if they're there
        if (benchmark.iloc[0, :].isnull().all()) & (numpy.isnan(series[0])):
            benchmark = benchmark.dropna()
            series = series.dropna()
        return benchmark.apply(lambda x: _r_squared(x = x, y = series))
    else:
        if (numpy.isnan(benchmark.iloc[0])) & (numpy.isnan(series.iloc[0])):
            benchmark = benchmark.dropna()
            series = series.dropna()
        return _r_squared(y = series, x = benchmark)



def r2_adj(series, benchmark):
    """
    The Adjusted R-Squared that incorporates the number of 
    independent variates using the `Formula Found of Wikipedia
    <http://en.wikipedia.org/wiki/Coefficient_of_determination#Adjusted_R2>_`

    :ARGS:

        series: :class:`pandas.Series` of asset returns

        benchmark: :class:`pandas.DataFrame` of benchmark returns to 
        explain the returns of the ``series``

        weights: :class:`pandas.Series` of weights to weight each column 
        of the benchmark

    :RETURNS:

        :class:float of the adjusted r-squared`
    """
    n = len(series)
    p = 1
    return 1 - (1 - r2(series, benchmark))*(n - 1)/(n - p - 1)  

def r2_mv_adj(x, y):
    """
    Returns the adjusted R-Squared for multivariate regression
    """
    n = len(y)
    p = x.shape[1]
    return 1 - (1 - r2_mv(x, y))*(n - 1)/(n - p - 1)

def r2_mv(x, y):   
    """
    Multivariate r-squared
    """
    ones = pandas.Series(numpy.ones(len(y)), name = 'ones')
    d = x.to_dict()
    d['ones'] = ones
    cols = ['ones']
    cols.extend(x.columns)
    X = pandas.DataFrame(d, columns = cols)
    beta = numpy.linalg.inv(X.transpose().dot(X)).dot(
        X.transpose().dot(y) )
    y_est = beta[0] + x.dot(beta[1:])
    ss_res = ((y_est - y)**2).sum()
    ss_tot = ((y - y.mean())**2).sum()
    return 1 - ss_res/ss_tot

def risk_adjusted_excess_return(series, benchmark, rfr = 0., 
                                freq = 'daily'):
    """
    Returns the MMRAP or the `Modigliani Risk Adjusted Performance 
    <http://en.wikipedia.org/wiki/Modigliani_risk-adjusted_performance>`_ 
    that calculates the excess return from the `Capital Allocation Line 
    <http://en.wikipedia.org/wiki/Capital_allocation_line>`_, at the 
    same level of risk (or volatility), specificaly,
        
    :ARGS:

        series: ``pandas.Series`` of prices

        benchmark: ``pandas.Series`` from which to compare ``series``

        rfr: ``float`` of the risk free rate

        freq: ``str`` of frequency, either ``daily, monthly, quarterly, 
        or yearly``

    :RETURNS:

        ``float`` of the risk adjusted excess performance

    .. note:: Calculating Risk Adjusted Excess Returns

       .. math::
    
          raer = r_p - \\left(\\textrm{SR}_b \\cdot \\sigma_p + 
          r_f\\right)

       Where,

       .. math::

          r_p &= \\textrm{annualized linear return} 
          \\\\
          \\textrm{SR}_b &= \\textrm{Sharpe Ratio of the benchmark} 
          \\\\
          \\sigma_p &= \\textrm{volatility of the portfolio}
          \\\\
          r_f &= \\textrm{Risk free rate}
    
    """
    def _risk_adjusted_excess_return(series, benchmark, rfr = 0., 
                                     freq = 'daily'):
        benchmark_sharpe = sharpe_ratio(benchmark, rfr, freq)
        annualized_ret = annualized_return(series, freq)
        series_vol = annualized_vol(series, freq)
        return annualized_ret - series_vol * benchmark_sharpe - rfr

    if isinstance(benchmark, pandas.DataFrame):
        return benchmark.apply(lambda x: _risk_adjusted_excess_return(
            series, x, rfr = rfr, freq = freq))
    else:
        return _risk_adjusted_excess_return(series, benchmark, 
                                            rfr = rfr, freq = freq)

def risk_contribution(mctr_series, weight_series):
    """
    Returns the risk contribution for each asset, given the marginal 
    contribution to risk ("mctr") and the ``weight_series`` of asset 
    weights

    :ARGS:

        mctr_series: :class:`pandas.Series` of the marginal risk 
        contribution 

        weight_series: :class:`pandas.Series` of weights of each asset

    :RETURNS:

        :class:`pandas.Series` of the risk contribution of each asset

    .. note:: Calculating Risk Contribution

        If :math:`RC_i` is the Risk Contribution of asset :math:`i`, and 
        :math:`\omega_i` is the weight of asset :math:`i`, then

        .. math::

            RC_i = mctr_i \\cdot \\omega_i
        
    
    .. seealso:: :meth:`mctr` for Marginal Contribution to Risk ("mctr") 
        as well as the `Risk Contribution <http://bit.ly/1eGmxJG>`_ 
        paper from MSCI Barra
    
    """
    return mctr_series.mul(weight_series)


def risk_contribution_as_proportion(mctr_series, weight_series):
    """
    Returns the proprtion of the risk contribution for each asset, given 
    the marginal contribution to risk ("mctr") and the ``weight_series`` 
    of asset weights

    :ARGS:

        mctr_series: :class:`pandas.Series` of the marginal risk 
        contribution 

        weight_series: :class:`pandas.Series` of weights of each asset

    :RETURNS:

        :class:`pandas.Series` of the proportional risk contribution 
        of each asset

    
    .. seealso:: :meth:`mctr` for Marginal Contribution to Risk ("mctr") 
        as well as the `Risk Contribution <http://bit.ly/1eGmxJG>`_ 
        paper from MSCI Barra
    
    """
    rc = mctr_series.mul(weight_series)
    return rc/rc.sum()
 
def rolling_ui(series, window = 21):
    """   
    returns the rolling ulcer index over a series for a given ``window``
    (instead of the squared deviations from the mean).
    
    :ARGS:
    
        series: ``pandas.Series`` of prices

        window: ``int`` of the size of the rolling window
        
    :RETURNS:
    
        ``pandas.Series``: of the rolling ulcer index

    .. code::

        import visualize_wealth.performance as vwp

        ui = vwp.rolling_ui(price_series, window = 252)

    """
    def _rolling_ui(series, window = 21):
        rui = pandas.Series(numpy.tile(numpy.nan, [len(series),]), 
                            index = series.index, name = 'rolling UI')
        j = 0
        for i in numpy.arange(window, len(series)):
            rui[i] = ulcer_index(series[j:i])
            j += 1
        return rui

    if isinstance(series, pandas.DataFrame):
        return series.apply(lambda x: _rolling_ui(x, window = window))
    else:
        return _rolling_ui(series)

def adj_sharpe_ratio(series, rfr = 0., freq = 'daily'):
    """
    Returns the `Ajusted Sharpe Ratio <http://en.wikipedia.org/wiki/Sharpe_ratio>`_ 
    of an asset, taking into account the kurtosis and skew of the returns.    time series
    
    :ARGS:

        series: ``pandas.Series`` of prices

        rfr: ``float`` of the risk free rate

        freq: ``str`` of frequency, either ``daily, monthly, quarterly, or 
        yearly``

    :RETURN:

        ``float`` of the Adjusted Sharpe Ratio

    .. note:: Calculating Sharpe 

        .. math::

            \\textrm{SR_{adj}} = \\textrm{SR} \\cdot (1 + \\frac{S}{6}\\cdot 
            \\textrm{SR} - \\frac{K - 3}{24} \\cdot \\textrm{SR}^2)
            \\textrm{where},

            R_p &= \\textrm{series annualized return} \\\\
            r_f &= \\textrm{Risk free rate} \\\\
            \\sigma &= \\textrm{Portfolio annualized volatility}

    """
    def _adj_sharpe_ratio(series, rfr = 0., freq = 'daily'):
        sr = sharpe_ratio(series, rfr = rfr, freq = freq)
        skew = log_returns(series).skew()
        kurt = log_returns(series).kurt()
        return sr * (1 + skew/6. * sr - (kurt - 3)/24 * sr**2)

    if isinstance(series, pandas.DataFrame):
        return series.apply(lambda x: _adj_sharpe_ratio(x, rfr = rfr, freq = freq))
    else:
        return _adj_sharpe_ratio(series, rfr = rfr, freq = freq)

def sharpe_ratio(series, rfr = 0., freq = 'daily'):
    """
    Returns the `Sharpe Ratio <http://en.wikipedia.org/wiki/Sharpe_ratio>`_ 
    of an asset, given a price series, risk free rate of ``rfr``, and 
    ``frequency`` of the 
    time series
    
    :ARGS:

        series: ``pandas.Series`` of prices

        rfr: ``float`` of the risk free rate

        freq: ``str`` of frequency, either ``daily, monthly, quarterly, or 
        yearly``

    :RETURN:

        ``float`` of the Sharpe Ratio

    .. note:: Calculating Sharpe 

        .. math::

            \\textrm{SR} = \\frac{(R_p - r_f)}{\\sigma} \\: 
            \\textrm{where},

            R_p &= \\textrm{series annualized return} \\\\
            r_f &= \\textrm{Risk free rate} \\\\
            \\sigma &= \\textrm{Portfolio annualized volatility}

    """
    def _sharpe_ratio(series, rfr = 0., freq = 'daily'):
        return (annualized_return(series, freq) - rfr)/annualized_vol(
            series, freq)

    if isinstance(series, pandas.DataFrame):
        return series.apply(lambda x: _sharpe_ratio(x, rfr = rfr, freq = freq))
    else:
        return _sharpe_ratio(series, rfr = rfr, freq = freq)


def sortino_ratio(series, freq = 'daily', rfr = 0.0):
    """
    Returns the `Sortino Ratio 
    <http://en.wikipedia.org/wiki/Sortino_ratio>`_, or excess returns 
    per unit downside volatility

    :ARGS:
    
        series: ``pandas.Series`` of prices
    
        freq: ``str`` of either ``daily, monthly, quarterly, or yearly``    
        indicating the frequency of the data ``default=`` daily

    :RETURNS:
    
        float of the Sortino Ratio

    .. note:: Calculating the Sortino Ratio

        There are several calculation methodologies for the Sortino 
        Ratio, this method using downside volatility, where
        
        .. math::

            \\textrm{Sortino Ratio} = \\frac{(R-r_f)}
            {\\sigma_\\textrm{downside}}
    
    .. code:: 

        import visualize_wealth.performance as vwp

        sortino_ratio = vwp.sortino_ratio(price_series, 
            frequency = 'monthly')
        
    """
    def _sortino_ratio(series, freq = 'daily'):
        return annualized_return(series, freq = freq)/downside_deviation(
            series, freq = freq)

    if isinstance(series, pandas.DataFrame):
        return series.apply(lambda x: _sortino_ratio(x, freq = freq))
    else:
        return _sortino_ratio(series, freq = freq)

def systematic_as_proportion(series, benchmark, freq = 'daily'):
    """
    Returns the systematic risk as proportion of total volatility

    :ARGS:

        series: ``pandas.Series`` of prices

        benchmark: ``pandas.Series`` to compare ``series`` against

        freq: ``str`` of frequency, either ``daily, monthly, quarterly, 
        or yearly``

    :RETURNS:

        ``float`` between (0, 1) representing the proportion of  volatility
        represented by systematic risk

    """
    def _systematic_as_proportion(series, benchmark, freq = 'daily'):
        fac = _interval_to_factor(freq)
        return systematic_risk(series, benchmark, freq) **2 / (
            annualized_vol(series, freq)**2)

    if isinstance(benchmark, pandas.DataFrame):
        return benchmark.apply(lambda x: _systematic_as_proportion(
            series, x, freq))
    else:
        return _systematic_as_proportion(series, benchmark, freq)


def systematic_risk(series, benchmark, freq = 'daily'):
    """
    Returns the systematic risk, or the volatility that is directly 
    attributable to the benchmark

    :ARGS:

        series: ``pandas.Series`` of prices

        benchmark: ``pandas.Series`` to compare ``series`` against

        freq: ``str`` of frequency, either ``daily, monthly, quarterly, or 
        yearly``

    :RETURNS:

        ``float`` of the systematic volatility (not variance)

    .. note::  Calculating Systematic Risk

        .. math::
            \\sigma_b &= \\textrm{Volatility of the Benchmark} \\\\
            \\sigma^2_{\\beta} &= \\textrm{Systematic Risk} \\\\
            \\beta &= \\frac{\\sigma^2_{s, b}}{\\sigma^2_{b}} \\: 
            \\textrm{then,}

            \\sigma^2_{\\beta} &= \\beta^2 \\cdot \\sigma^2_{b}
            \\Rightarrow \\sigma_{\\beta} &= \\beta \\cdot \\sigma_{b}
    """
    def _systematic_risk(series, benchmark, freq = 'daily'):
        bench_rets = log_returns(benchmark)
        benchmark_vol = annualized_vol(benchmark)
        return benchmark_vol * beta(series, benchmark)

    if isinstance(benchmark, pandas.DataFrame):
        return benchmark.apply(lambda x: _systematic_risk(series, x, freq))
    else:
        return _systematic_risk(series, benchmark, freq)

def tracking_error(series, benchmark, freq = 'daily'):
    """
    Returns a ``float`` of the `Tracking Error 
    <http://en.wikipedia.org/wiki/Tracking_error>`_ or standard 
    deviation of the active returns
      
    :ARGS:

        series: ``pandas.Series`` of prices

        benchmark: ``pandas.Series`` to compare ``series`` against

        freq: ``str`` of frequency, either ``daily, monthly, quarterly, 
        or yearly`` 


    :RETURNS:

        ``float`` of the tracking error

    .. note:: Calculating Tracking Error

        Let :math:`r_{a_i} =` "Active Return" for period :math:`i`, to 
        calculate the compound linear difference between :math:`r_s` 
        and :math:`r_b` is,

        .. math::

            r_{a_i} = \\frac{(1+r_{s_i})}{(1+r_{b_i})}-1

        Then,

        .. math:: 

            \\textrm{TE} &= \\sigma_a \\cdot \\sqrt{k} \\\\
            k &= \\textrm{Annualization factor}

    """
    def _tracking_error(series, benchmark, freq = 'daily'):
        fac = _interval_to_factor(freq)
        series_rets = linear_returns(series)
        bench_rets = linear_returns(benchmark)
        return ((1 + series_rets).div(
            1 + bench_rets) - 1).std()*numpy.sqrt(fac)

    if isinstance(benchmark, pandas.DataFrame):
        return benchmark.apply(lambda x: _tracking_error(
            series, x, freq = freq))
    else:
        return _tracking_error(series, benchmark, freq = freq)

    
def ulcer_index(series):
    """
    Returns the ulcer index of  the series, which is defined as the 
    squared drawdowns (instead of the squared deviations from the mean).  
    Further explanation can be found at `Tanger Tools 
    <http://www.tangotools.com/ui/ui.htm>`_
    
    :ARGS:
    
        series: ``pandas.Series`` of prices

    :RETURNS:
    
        :float: the maximum drawdown of the period, expressed as a 
        positive number

    .. code::

        import visualize_wealth.performance as vwp

        ui = vwp.ulcer_index(price_series)

    """
    def _ulcer_index(series):
        dd = 1. - series/series.cummax()
        ssdd = numpy.sum(dd**2)
        return numpy.sqrt(numpy.divide(ssdd, series.shape[0] - 1))
    if isinstance(series, pandas.DataFrame):
        return series.apply(_ulcer_index)
    else:
        return _ulcer_index(series)


def upcapture(series, benchmark):
    """
    Returns the proportion of ``series``'s cumulative positive returns 
    to ``benchmark``'s cumulative  returns, given benchmark's returns 
    were positive in that period

    :ARGS:

        series: :class:`pandas.Series` of prices

        benchmark: :class:`pandas.Series` of prices to compare ``series`` 
        against

    :RETURNS:

        float: of the upcapture of cumulative positive returns

    .. seealso:: :py:data:`median_upcature(series, benchmark)`
    
    """
    def _upcapture(series, benchmark):
        series_rets = log_returns(series)
        bench_rets = log_returns(benchmark)
        index = bench_rets > 0.
        return series_rets[index].mean() / bench_rets[index].mean()

    if isinstance(benchmark, pandas.DataFrame):
        return benchmark.apply(lambda x: _upcapture(series, x))
    else:
        return _upcapture(series, benchmark)

def upside_deviation(series, freq = 'daily'):
    """
    Returns the volatility of the returns that are greater than zero

    :ARGS:

        series: :class:`pandas.Series` of prices

        freq: ``str`` of frequency, either ``daily, monthly, quarterly, or 
        yearly``

    :RETURNS:

        ``float`` of the upside standard deviation
    """
    def _upside_deviation(series, freq = 'daily'):
        fac = _interval_to_factor(freq)
        series_rets = log_returns(series)
        index = series_rets > 0.
        return series_rets[index].std()*numpy.sqrt(fac)

    if isinstance(series, pandas.DataFrame):
        return series.apply(lambda x: _upside_deviation(x, freq = freq))
    else:
        return _upside_deviation(series, freq)

def var_cf(series, p = .01):
    """
    VaR (Value at Risk), using the `Cornish Fisher Approximation
    <http://en.wikipedia.org/wiki/Cornish%E2%80%93Fisher_expansion>`_.

    :ARGS:

        series: :class:`pandas.Series` or :class:`pandas.DataFrame` 
        of prices

        p: :class:`float` of the :math:`\\alpha` percentile

    :RETURNS:

        :class:`float` or :class:`pandas.Series` of the VaR, where skew 
        and kurtosis are used to adjust the tail density estimation 
        (using the Cornish Fisher Approximation)
    
    """
    series_rets = log_returns(series)
    mu, sigma = series_rets.mean(), series_rets.std()
    skew, kurt = series_rets.skew(), series_rets.kurtosis() - 3.
    v = lambda alpha: scipy.stats.distributions.norm.ppf(1 - alpha)
    V = v(p)+(1-v(p)**2)*skew/6+(5*v(p)-2*v(p)**3)*skew**2/36 + (
        v(p)**3-3*v(p))*kurt/24
    return numpy.exp(sigma * V - mu) - 1

def var_norm(series, p = .01):
    """
    Value at Risk ("VaR") of the :math:`p = \\alpha` quantile, defines 
    the loss, such that there is an :math:`\\alpha` percent chance of 
    a loss, greater than or equal to :math:`\\textrm{VaR}_\\alpha`. 
    :meth:`var_norm` fits a normal distribution to the log returns of 
    the series, and then estimates the :math:`\\textrm{VaR}_\\alpha`

    :ARGS:

        series: :class:`pandas.Series` or :class:`pandas.DataFrame` 
        of prices

        p: :class:`float` of the :math:`\\alpha` quantile for which to 
        estimate VaR

    :RETURNS:

        :class:`float` or :class:`pandas.Series` of VaR

    .. note:: Derivation of Value at Risk

        Let :math:`Y \\sim N(\\mu, \\sigma^2)`, we choose 
        :math:`y_\\alpha` such that 
        :math:`\\mathbb{P}(Y < y_\\alpha) = \\alpha`. 

        Then,

        .. math::

            \\mathbb{P}(Y < y_\\alpha) &= \\alpha \\\\
            \\Rightarrow \\mathbb{P}(\\frac{Y - \\mu}{\\sigma} < 
            \\frac{y_\\alpha - \\mu}{\\sigma}) &= \\alpha 
            \\\\
            \\Rightarrow \\mathbb{P}(Z < \\frac{y_\\alpha - 
            \\mu}{\sigma} &= \\alpha
            \\\\
            \\Rightarrow \\Phi(\\frac{y_\\alpha - \\mu}{\\sigma} ) 
            &= \\alpha, 

        where :math:`\\Phi(.)` is the standard normal cdf operator.
        Then using the inverse of the function :math:`\\Phi`, 
        we have:

        .. math::

            \\Phi^{-1}( \\Phi(\\frac{y_\\alpha - \\mu}{\\sigma} ) ) 
            &= \\Phi^{-1}(\\alpha) 
            \\\\
            \\Rightarrow \\Phi^{-1}(\\alpha)\\cdot\\sigma + \\mu 
            = y_\\alpha 

        But :math:`y_\\alpha` is negative and VaR is always 
        positive, so,

        .. math:: 

            VaR_\\alpha = -y_\\alpha &= -\\Phi^{-1}
            (\\alpha)\\cdot\\sigma - \\mu
            \\\\
            &= \\Phi^{-1}(1 - \\alpha) - \\mu \\\\

    .. seealso:: :meth:var_cf :meth:var_np
             
    """
    def _var_norm(series, p):
        series_rets = log_returns(series)
        mu, sigma = series_rets.mean(), series_rets.std()
        v = lambda alpha: scipy.stats.distributions.norm.ppf(1 - alpha)
        return numpy.exp(sigma * v(p) - mu) - 1

    if isinstance(series, pandas.DataFrame):
        return series.apply(lambda x: _var_norm(x, p = p))
    else:
        return _var_norm(series, p = p)

def var_np(series, p = .01):
    """    
    Return the non-parametric VaR (non-parametric estimate) for a given 
    percentile, i.e. the loss for which there is less than a 
    ``percentile`` chance of exceeding in a period of `freq`.

    :ARGS:
    
        series: ``pandas.Series`` of prices

        freq:``str`` of either ``daily, monthly, quarterly, or yearly``    
        indicating the frequency of the data ``default = daily``

        percentile: ``float`` of the percentile at which to calculate VaR
        
    :RETURNS:
    
        float of the Value at Risk given a ``percentile``

    .. code::

        import visualize_wealth.performance as vwp

        var = vwp.value_at_risk(price_series, frequency = 'monthly', 
        percentile = 0.1)
    
    """
    def _var_np(series, p = .01):
        
        series_rets = linear_returns(series)
        #loss is always reported as positive
        return -1 * (numpy.percentile(series_rets, p*100.))

    if isinstance(series, pandas.DataFrame):
        return series.apply(lambda x: _var_np(x, p = p))
    else:
        return _var_np(series, p = p)

def _interval_to_factor(interval):
    factor_dict = {'daily': 252, 'monthly': 12, 'quarterly': 4, 
                   'yearly': 1}
    return factor_dict[interval] 
    
def _bool_interval_index(pandas_index, interval = 'monthly'):
    """
    creates weekly, monthly, quarterly, or yearly intervals by creating a
    boolean index to be passed visa vie DataFrame.ix[bool_index, :]
    """
    weekly = lambda x: x.weekofyear[1:] != x.weekofyear[:-1]
    monthly = lambda x: x.month[1:] != x.month[:-1]
    yearly = lambda x: x.year[1:] != x.year[:-1]
    ldom = lambda x: x.month[1:] != x.month[:-1]
    fdom = lambda x: numpy.append(False, x.month[1:]!=x.month[:-1])
    qt = lambda x: numpy.append(False, x.quarter[1:]!=x.quarter[:-1])
    time_dict = {'weekly':weekly, 'monthly': monthly, 'quarterly': qt, 
                 'yearly': yearly, 'ldom':ldom, 'fdom':fdom}

    return time_dict[interval](pandas_index)
