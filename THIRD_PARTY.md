# Dependencies and external methods

The Go executables use the Go standard library and contain no vendored modules. Python analysis uses NumPy (BSD-3-Clause), SciPy (BSD-3-Clause), pandas (BSD-3-Clause), and Matplotlib (PSF-based license). These packages are installed separately and retain their upstream licenses.

The optional `*_vldb*` protocol arms use calibration constants attributed in the source to the related self-sizing IBLT manuscript (bibliography key `wu2026selfsizing`). They are defined only for k = 3, u = 0.01, and selected table sizes. The primary smoke experiment uses the Skellam, Gaussian, and oracle arms. Complete the public bibliographic identifier before a citable release.

The source snapshot records first-party research code copied from the originating research workspace. It does not include third-party papers or the research workspace's private server configuration.
