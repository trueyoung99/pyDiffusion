"""
The fsa module provides tools to perform Forward Simulation Analysis (FSA).
"""
import matplotlib as plt
from pydiffusion.core import DiffSystem
from pydiffusion.utils import error_profile, step, matanocalc, mesh
from pydiffusion.Dmodel import Dadjust
from pydiffusion.plot import profileplot, DCplot, SFplot
from pydiffusion.simulation import mphSim


def FSA(profile_exp, profile_sm, diffsys, time, Xlim=[], n=[400, 500]):
    """
    Forward Simulation Analysis

    Parameters
    ----------
    profile_exp : DiffProfile
        Experimental diffusion profile, used for comparison with simulation
        results.
    profile_sm : DiffProfile
        Diffusion profile after data smooth on experimental profile.
    diffsys : DiffSystem
        Diffusion coefficients
    time : float
        Diffusion time in seconds
    Xlim : list (float), optional
        Passed to pydiffusion.Dmodel.SF, pydiffusion.utils.step.
        Indicates the left and right concentration limits for calculation.
        Default value = [profile.X[0], profile.X[-1]].
    n : list
        Passed to pydiffusion.utils.mesh.
        Meshing number range, default = [400, 500].

    Returns
    -------
    profile_sim : DiffProfile
        Simulated diffusion profile after FSA.
    diffsys_sim : DiffSystem
        Calculated diffusion efficients by FSA.
    """
    # Create step profile on meshed grids
    dism = mesh(profile_sm, diffsys, n)
    matano = matanocalc(profile_sm, Xlim)
    profile_init = step(dism, matano, diffsys, Xlim)

    # Determine the stop criteria of forward simulations
    error_sm = error_profile(profile_sm, profile_exp)
    ipt = input('Default error = %.6f\nInput the stop criteria of error: [%.6f]'
                % (error_sm, error_sm*2))
    error_stop = error_sm*2 if ipt == '' else float(ipt)

    # If there is no Xspl info in diffsys, use whole-phase mode
    # else: ask if use whole-phase or per-point mode
    if diffsys.Xspl is not None:
        ipt = input('Use whole-phase mode? [n]\n(The shape of diffusivity curve does not change')
        pp = False if 'y' in ipt or 'Y' in ipt else True
    else:
        pp = False

    # Diffusion coefficients used for forward simulations
    diffsys_sim = DiffSystem(diffsys.Xr, diffsys.Dfunc, Xspl=diffsys.Xspl)

    # Plot FSA status
    fig = plt.figure(figsize=(16, 6))
    ax1, ax2 = fig.add_subplot(121), fig.add_subplot(122)
    profileplot(profile_exp, ax1, ls='none', marker='o', c='b', fillstyle='none')
    profileplot(profile_sm, ax1, ls='-', c='g', lw=1)
    SFplot(profile_sm, time, Xlim, ax2, ls='none', c='b', marker='.')
    DCplot(diffsys_sim, ax2, ls='-', c='r', lw=2)
    plt.draw()
    plt.pause(1.0)

    n_sim = 0
    while True:

        # Simulation
        n_sim += 1
        profile_sim = mphSim(profile_init, diffsys_sim, time)
        error_sim = error_profile(profile_sim, profile_exp)
        print('Simulation %i, error = %f(%f)' % (error_sim, error_stop))

        # Plot simulation results
        ax1.cla()
        ax2.cla()
        profileplot(profile_exp, ax1, ls='none', marker='o', c='b', fillstyle='none')
        profileplot(profile_sm, ax1, ls='-', c='g', lw=1)
        profileplot(profile_sim, ax1, ls='-', c='r', lw=2)
        SFplot(profile_sm, time, Xlim, ax2, ls='none', c='b', marker='.')
        DCplot(diffsys_sim, ax2, ls='-', c='r', lw=2)
        plt.draw()
        plt.pause(.1)

        # DC adjust
        Dfunc_adjust = [0] * diffsys_sim.Np

        # If error > stop criteria, continue simulation by auto DC adjustment
        if error_sim > error_stop:
            for ph in range(diffsys_sim.Np):
                Dfunc_adjust[ph] = Dadjust(profile_sm, profile_sim, diffsys_sim, ph, pp)
            diffsys_sim.Dfunc = Dfunc_adjust

        # If error < stop criteria or simulate too many times
        if error_sim <= error_stop or n_sim > 9:

            # Ask if exit
            ipt = 'Satisfied with FSA? [n]'
            if 'y' or 'Y' in ipt:
                break

            # If use per-point mode
            if diffsys_sim.Xspl is not None:
                ipt = input('Use per-point mode? [y]')
                pp = False if 'n' in ipt or 'N' in ipt else True
                if pp:
                    for ph in range(diffsys_sim.Np):
                        Dfunc_adjust[ph] = Dadjust(profile_sm, profile_sim, diffsys_sim, ph, pp)
                    diffsys_sim.Dfunc = Dfunc_adjust
                    continue

            # Whole-phase mode, ask if use manual input for
            pp = False
            ipt = input('Whole-phase mode\nManually input for each phase? [n]')
            manual = True if 'y' in ipt or 'Y' in ipt else False
            for ph in range(diffsys_sim.Np):
                if manual:
                    ipt = input('Input deltaD for phase # %i:\n \
                                 DC = DC * 10^deltaD, default deltaD = auto' % ph+1)
                    deltaD = float(ipt) if ipt != '' else None
                else:
                    deltaD = None
                Dfunc_adjust[ph] = Dadjust(profile_sm, profile_sim, diffsys_sim, ph, pp, deltaD)

            # Apply the adjustment to diffsys_sim
            diffsys_sim.Dfunc = Dfunc_adjust

            DCplot(diffsys_sim, ax2, ls='-', c='m', lw=2)
            plt.draw()
            plt.pause(.1)

    return profile_sim, diffsys_sim