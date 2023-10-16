# Copyright 2013-2023 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import os
import sys

from spack.package import *


class Vasp(CMakePackage, CudaPackage):
    """
    The Vienna Ab initio Simulation Package (VASP)
    is a computer program for atomic scale materials modelling,
    e.g. electronic structure calculations
    and quantum-mechanical molecular dynamics, from first principles.
    """

    homepage = "https://vasp.at"
    url = "file://{0}/vasp.5.4.4.pl2.tgz".format(os.getcwd())
    manual_download = True

    version("6.4.2", sha256="a6cacdd43e7dc50ee585850cbe89bdf5e7fcb66237e2e6a8919cb8ee250d689d")
    version("6.3.2", sha256="a6cacdd43e7dc50ee585850cbe89bdf5e7fcb66237e2e6a8919cb8ee250d689d")
    version("6.3.0", sha256="adcf83bdfd98061016baae31616b54329563aa2739573f069dd9df19c2071ad3")
    version("6.2.0", sha256="49e7ba351bd634bc5f5f67a8ef1e38e64e772857a1c02f602828898a84197e25")
    version("6.1.1", sha256="e37a4dfad09d3ad0410833bcd55af6b599179a085299026992c2d8e319bf6927")
    version("5.4.4.pl2", sha256="98f75fd75399a23d76d060a6155f4416b340a1704f256a00146f89024035bc8e")
    version("5.4.4", sha256="5bd2449462386f01e575f9adf629c08cb03a13142806ffb6a71309ca4431cfb3")

    resource(
        name="vaspsol",
        git="https://github.com/henniggroup/VASPsol.git",
        tag="V1.0",
        when="+vaspsol",
    )

    variant("profiling", default=False, description="Enable profiling")
    variant("collective", default=True, description="Enable collective MPI calls")
    variant("avoidalloc", default=False, description="Enable avoidance of automatic allocations")
    variant("vasp6", default=True, when="@6:", description="Enable VASP 6.x features")
    variant("tbdyn", default=True, description="Enable advanced molecular dynamics")
    variant("fock_dblbuf", default=False, description="Enable double buffering for exchange potential")
    variant("shmem", default=False, description="Enable shared memory for reduced memory usage")
    variant("shmem_bcast", default=False, description="")
    variant("shmem_rproj", default=False, description="")
    variant("sysv", default=False, description="")
    variant("openmp", default=True, description="")
    variant("fftlib", when="+openmp", default=True, description="")
    variant("scalapack", default=False, description="")
    variant("hdf5", default=False, description="")
    variant("wannier90", default=False, description="")
    variant("libxc", default=False, description="")
    variant("ncclp2p", when="+cuda", default=True, description="")


    with when("+openmp"):
        conflicts("^fftw~openmp")
        conflicts("^amdfftw~openmp")
        conflicts("^amdblis threads=none")
        conflicts("^amdblis threads=pthreads")
        conflicts("^openblas threads=none")
        conflicts("^openblas threads=pthreads")

    requires(
        "%nvhpc",
        when="+cuda",
        msg="NVHPC compiler is required for CUDA support"
    )

    depends_on("blas")
    depends_on("lapack")
    depends_on("fftw-api@3:")
    depends_on("fftw-api@3:+openmp", when="+openmp")
    depends_on("mpi", type=("build", "link", "run"))
    depends_on("scalapack", when="+scalapack")
    depends_on("nvhpc~blas~lapack", when="+cuda")
    depends_on("hdf5+fortran", when="+hdf5")
    depends_on("libxc~cuda", when="+libxc")
    depends_on("wannier90", when="+wannier90")

    conflicts(
        "%gcc@:8", msg="GFortran before 9.x does not support all features needed to build VASP"
    )

    patch("cmake.patch")

    def cmake_args(self):
        spec = self.spec

        args = [
            self.define_from_variant("VASP_PROFILING", "profiling"),
            self.define_from_variant("VASP_COLLECTIVE", "collective"),
            self.define_from_variant("VASP_AVOIDALLOC", "avoidalloc"),
            self.define_from_variant("VASP_VASP6", "vasp6"),
            self.define_from_variant("VASP_TBDYN", "tbdyn"),
            self.define_from_variant("VASP_FOCK_DBLBUF", "fock_dblbuf"),
            self.define_from_variant("VASP_SHMEM", "shmem"),
            self.define_from_variant("VASP_SHMEM_BCAST", "shmem_bcast"),
            self.define_from_variant("VASP_SHMEM_RPROJ", "shmem_rproj"),
            self.define_from_variant("VASP_SYSV", "sysv"),
            self.define_from_variant("VASP_OPENMP", "openmp"),
            self.define_from_variant("VASP_FFTLIB", "fftlib"),
            self.define_from_variant("VASP_SCALAPACK", "scalapack"),
            self.define_from_variant("VASP_HDF5", "hdf5"),
            self.define_from_variant("VASP_WANNIER90", "wannier90"),
            self.define_from_variant("VASP_LIBXC", "libxc"),
            self.define_from_variant("VASP_CUDA", "cuda"),
            self.define_from_variant("VASP_NCCLP2P", "ncclp2p"),
            "-DVASP_LIBBEEF=OFF",
            "-DVASP_DFTD4=OFF",
        ]


        if spec.satisfies("+cuda"):
            cuda_arch = self.spec.variants["cuda_arch"].value
            if cuda_arch[0] != "none":
                args += [self.define("CMAKE_CUDA_ARCHITECTURES", cuda_arch)]
            args += [self.define("QD_ROOT", join_path(spec["nvhpc"].prefix, "Linux_%s" % self.spec.target.family, spec["nvhpc"].version))]

        if "^armpl-gcc threads=openmp" in spec:
            args += ["-DBLA_VENDOR=Arm_mp"]
        elif "^armpl-gcc threads=none" in spec:
            args += ["-DBLA_VENDOR=Arm"]

        return args

    #  def setup_run_environment(self, env):
    #      spec = self.spec
    #      if "^nvhpc" in spec:
    #          env.prepend_path("CMAKE_PREFIX_PATH", spec["nvhpc"].prefix)
    #          env.prepend_path("CMAKE_PREFIX_PATH", join_path(spec["nvhpc"].prefix, "Linux_%s" % self.spec.target.family, spec["nvhpc"].version))
