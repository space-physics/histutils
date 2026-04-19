#!/usr/bin/env python3
"""
A demo of using Wiener filters efficiently on noisy auroral video
"""

import cv2
import h5py
import numpy as np
from numpy.fft import fft2, fftshift
from scipy.signal import wiener
import skimage.transform

import matplotlib.pyplot as plt

# from matplotlib.colors import LogNorm

fn = "tests/testframes_cam0.h5"  # indistinct aurora

with h5py.File(fn, "r") as f:
    imgs = f["/rawimg"][:].astype(float)  # float for fft

im = imgs[0, ...]
im2 = imgs[1, ...]

sim = skimage.transform.resize(im, (im.shape[1] // 8, im.shape[0] // 8))
sim2 = skimage.transform.resize(im2, (im2.shape[1] // 8, im2.shape[0] // 8))
# %% optical flow
flow = cv2.calcOpticalFlowFarneback(
    im,
    im2,
    None,
    pyr_scale=0.5,
    levels=1,
    winsize=3,
    iterations=5,
    poly_n=3,
    poly_sigma=1.5,
    flags=1,
)
flowmag = np.hypot(flow[..., 0], flow[..., 1])

plt.figure(5).clf()
fg, axs = plt.subplots(1, 2, num=5)

ax = axs[0]
h = ax.imshow(flowmag, cmap="cubehelix_r", origin="bottom")
fg.colorbar(h, ax=ax)
ax.set_title("Farneback estimate optical flow")
ax.set_xlabel("x")
ax.set_ylabel("y")

sflow = cv2.calcOpticalFlowFarneback(
    sim,
    sim2,
    None,
    pyr_scale=0.5,
    levels=1,
    winsize=3,
    iterations=5,
    poly_n=3,
    poly_sigma=1.5,
    flags=1,
)
sflowmag = np.hypot(sflow[..., 0], sflow[..., 1])

ax = axs[1]
h = ax.imshow(sflowmag, cmap="cubehelix_r", origin="bottom")
fg.colorbar(h, ax=ax)
ax.set_title("Farneback estimate optical flow: downsize by 8")
ax.set_xlabel("x")
ax.set_ylabel("y")


# %% temporal derivative
dt = im2 - im
plt.figure(4).clf()
fg, axs = plt.subplots(1, 2, num=4)
ax = axs[0]
h = ax.imshow(dt, cmap="bwr", origin="bottom", vmin=-2000, vmax=2000)
fg.colorbar(h, ax=ax)
ax.set_xlabel("x")
ax.set_ylabel("y")
ax.set_title("d/dt")

ax = axs[1]
h = ax.imshow(abs(dt), cmap="cubehelix_r", origin="bottom", vmin=0, vmax=2000)
fg.colorbar(h, ax=ax)
ax.set_xlabel("x")
ax.set_ylabel("y")
ax.set_title("|d/dt|")
# %% spatial derivative
u, v = np.diff(im, axis=1), np.diff(im, axis=0)
uvmag = np.hypot(u[1:, :], v[:, 1:])

plt.figure(3).clf()
ax = plt.figure(3).gca()
ax.hist(im.ravel(), bins=128)
ax.set_yscale("log")
ax.set_title("hist: image")
ax.set_xlabel("16-bit Data numbers")
ax.set_ylabel("occurrences")
ax.axvline(np.median(im), linestyle="--", color="red", label="median")
ax.axvline(im.mean(), linestyle="-.", color="black", label="mean")
ax.legend()

plt.figure(2).clf()
fg, axs = plt.subplots(1, 2, num=2)

ax = axs[0]
h = ax.imshow(uvmag, cmap="cubehelix_r", vmin=500, vmax=4000, origin="bottom")  # norm=LogNorm(),
fg.colorbar(h, ax=ax)
ax.set_title("|dx,dy|")
ax.set_xlabel("x")
ax.set_ylabel("y")


ax = axs[1]
ax.hist(uvmag.ravel(), bins=128)
ax.set_yscale("log")
# ax.set_xlim((None,5000))
ax.axvline(np.median(uvmag), linestyle="--", color="red", label="median")
ax.axvline(np.mean(uvmag), linestyle="--", color="green", label="mean")
ax.legend()
ax.set_title("hist: |dx,dy|")
ax.set_ylabel("occurrences")
ax.set_xlabel("|flow|")
# %%
plt.figure(1).clf()
fg, ax = plt.subplots(2, 2, num=1)

hi = ax[0, 0].imshow(im)
ax[0, 0].set_title("raw image")
fg.colorbar(hi, ax=ax[0, 0])

# %%
Im = fft2(im)

hf = ax[1, 0].imshow(20 * np.log10(np.absolute(fftshift(Im))), cmap="cubehelix_r")
ax[1, 0].set_title("F(im)")
fg.colorbar(hf, ax=ax[1, 0])
hf.set_clim((90, None))
# %%
fim = wiener(im, 7)

hf = ax[0, 1].imshow(fim, cmap="cubehelix_r")
ax[0, 1].set_title("filtered image")
fg.colorbar(hf, ax=ax[0, 1])
# %%
Fim = fft2(fim)
hf = ax[1, 1].imshow(20 * np.log10(np.absolute(fftshift(Fim))))
ax[1, 1].set_title("F(fim)")
fg.colorbar(hf, ax=ax[1, 1])
hf.set_clim((90, None))

plt.show()
