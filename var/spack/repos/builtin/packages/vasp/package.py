# Copyright 2013-2023 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import os
import sys

from spack.package import *


class Vasp(MakefilePackage, CudaPackage):
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

    variant("openmp", default=False, description="Enable openmp build")
    variant("scalapack", default=False, description="Enables build with SCALAPACK")
    variant("cuda", default=False, description="Enables running on Nvidia GPUs")
    variant("fftlib", default=False, description="Enables fftlib build")
    variant(
        "vaspsol",
        default=False,
        description="Enable VASPsol implicit solvation model\n"
        "https://github.com/henniggroup/VASPsol",
    )
    variant("shmem", default=False, description="Enable use_shmem build flag")
    variant("hdf5", default=True, description="Enable hdf5 support")


    with when("+openmp"):
        conflicts("^fftw~openmp")
        conflicts("^amdfftw~openmp")
        conflicts("^amdblis threads=none")
        conflicts("^amdblis threads=pthreads")
        conflicts("^openblas threads=none")
        conflicts("^openblas threads=pthreads")

    with when("+fftlib"):
        conflicts("@:6.1.1", msg="fftlib support started from 6.2.0")
        conflicts("~openmp", msg="fftlib is intended to be used with openmp")


    depends_on("rsync", type="build")
    depends_on("blas")
    depends_on("lapack")
    depends_on("fftw-api@3:")
    depends_on("fftw-api@3:+openmp", when="+openmp")
    depends_on("mpi", type=("build", "link", "run"))
    depends_on("scalapack", when="+scalapack")
    depends_on("nvhpc~blas~lapack", when="+cuda")
    depends_on("hdf5+fortran", when="+hdf5")

    conflicts(
        "%gcc@:8", msg="GFortran before 9.x does not support all features needed to build VASP"
    )
    conflicts("+vaspsol", when="+cuda", msg="+vaspsol only available for CPU")
    conflicts("+openmp", when="@:6.1.1", msg="openmp support started from 6.2")

    def edit(self, spec, prefix):
        if "+vaspsol" in spec:
            copy("VASPsol/src/solvation.F", "src/")

        c_flags = []
        cxx_flags = ["-std=c++11"]
        ft_flags = []
        ft_flags_lib = []
        nvft_flags = []
        nvft_flags_lib = []
        ft_compiler = self.compiler.fc
        include_flags = [
                spec["fftw-api"].headers.include_flags,
                spec["blas"].headers.include_flags,
                spec["mpi"].headers.include_flags
        ]
        include_flags.extend(["-I{}".format(libdir) for libdir in spec["mpi"].libs.directories])
        link_flags = [
                "-lstdc++",
                spec["fftw-api"].libs.ld_flags,
                spec["blas"].libs.ld_flags,
                spec["mpi"].libs.ld_flags,
        ]

        free_flags = []
        nv_free_flags = []
        objects = ["fftmpiw.o", "fftmpi_map.o", "fftw3d.o", "fft3dlib.o"]

        internal_libs = []


        preprocess_flags = [
            "-DMPI -DMPI_BLOCK=8000",
            "-Duse_collective",
            "-DCACHE_SIZE=4000",
            "-Davoidalloc",
            "-Duse_bse_te",
            "-Dtbdyn",
            "-Dvasp6",
            "-DscaLAPACK",
            "-Dfock_dblbuf"
        ]

        if "%gcc" in spec:
            free_flags.extend(["-ffree-form", "-ffree-line-length-none"])
            ft_flags.extend(["-w", "-ffpe-summary=none", "-fallow-argument-mismatch"])
            preprocess_flags.extend(["-E", "-C", "-w"])

        if "%gcc@10:" in spec:
            ft_flags.append("-fallow-argument-mismatch")

        if "+cuda" in spec:
            nvhpc_prefix = join_path(spec["nvhpc"].prefix, "Linux_%s" % self.spec.target.family, spec["nvhpc"].version)
            qd_prefix = join_path(nvhpc_prefix, "compilers", "extras", "qd")

            objects.extend(["fftw3d_gpu.o", "fftmpiw_gpu.o"])
            ft_compiler = join_path(nvhpc_prefix, "compilers", "bin", "nvfortran")

            nv_free_flags.extend(["-Mfree"])
            nvft_flags.extend(["-Mbackslash", "-Mlarge_arrays"])
            nvft_flags.extend(["-acc", "-gpu={},cuda{}".format(",".join(["cc{}".format(arch) for arch in self.spec.variants["cuda_arch"].value]), spec["cuda"].version.up_to(2))])
            link_flags.extend(["-cudalib=cublas,cusolver,cufft,nccl", "-cuda", "-L{}".format(join_path(qd_prefix, "lib")), "-lqdmod", "-lqd"])
            include_flags.append("-I{}".format(join_path(qd_prefix, "include", "qd")))
            preprocess_flags.extend(["-D_OPENACC", "-DUSENCCL", "-DUSENCCLP2P", "-Dqd_emulate"])
            nvft_flags_lib.append("-Mfixed")


            # -Mfixed -Mfree order. Otherwise nvfortran throws error
            # add -Mfixed only to FFLAGS_LIB

        if "+openmp" in spec:
            c_flags.append(self.compiler.openmp_flag)
            cxx_flags.append(self.compiler.openmp_flag)
            preprocess_flags.append("-D_OPENMP")

            if "+cuda" in spec:
                nvft_flags.append(self.compiler.openmp_flag)
                link_flags.append(self.compiler.openmp_flag)
            else:
                ft_flags.append("-mp")
                link_flags.append("-mp")

            # add internal fftlib for openmp as is recommended
            preprocess_flags.append("-Dsysv")
            internal_libs.append("fftlib")
            link_flags.append("fftlib.o")

        if "+hdf5" in spec:
            link_flags.append(spec["hdf5"].libs.ld_flags)
            include_flags.append(spec["hdf5"].headers.include_flags)
            preprocess_flags.append("-DVASP_HDF5")

        #  if "+shmem" in spec:
        #      preprocess_flags.append("-Duse_shmem")

        if "+scalapack" in spec:
            link_flags.append(spec["scalapack"].libs.ld_flags)
            include_flags.append(spec["scalapack"].headers.include_flags)

        # generate makefile
        makefile_inc = []

        if "+cuda" in spec:
            ft_flags = nvft_flags
            free_flags = nv_free_flags
            ft_flags_lib = nvft_flags_lib

        makefile_inc.append("CPP = {} {} {}".format(self.compiler.cc, " ".join(preprocess_flags), "$*$(FUFFIX) >$*$(SUFFIX)"))
        makefile_inc.append("CPP_LIB = $(CPP)")
        makefile_inc.append("FC = {}".format(ft_compiler))
        makefile_inc.append("FCL = {}".format(ft_compiler))
        makefile_inc.append("FC_LIB = {}".format(ft_compiler))
        makefile_inc.append("CC_LIB = {}".format(self.compiler.cc))
        makefile_inc.append("CXX_PARS = {}".format(self.compiler.cxx))

        makefile_inc.append("OBJECTS = fftmpiw.o fftmpi_map.o fftw3d.o fft3dlib.o")
        makefile_inc.append("FREE = {}".format(" ".join(free_flags)))
        makefile_inc.append("FREE_LIB = {}".format(" ".join(free_flags)))
        makefile_inc.append("LLIBS = {}".format(" ".join(link_flags)))
        makefile_inc.append("INCS = {}".format(" ".join(include_flags)))
        makefile_inc.append("FFLAGS = {}".format(" ".join(ft_flags)))
        makefile_inc.append("OFLAG = -O2")
        makefile_inc.append("OFLAG_IN = $(OFLAG)")
        makefile_inc.append("FFLAGS_LIB = -O2 {}".format(" ".join(ft_flags_lib)))
        makefile_inc.append("CFLAGS_LIB = -O2")
        makefile_inc.append("DEBUG = -O0")

        makefile_inc.append("CXX_FFTLIB = {} {} {}".format(self.compiler.cxx, self.compiler.openmp_flag, "-std=c++11 -DFFTLIB_THREADSAFE"))
        makefile_inc.append("INCS_FFTLIB = -I./include {}".format(spec["fftw-api"].headers.include_flags))

        if len(internal_libs) > 1:
            makefile_inc.append("LIBS += {}".format(" ".join(internal_libs)))


        print("\n", file=sys.stderr)
        print(spec["mpi"].libs, file=sys.stderr)
        print("\n", file=sys.stderr)
        print("\n".join(makefile_inc), file=sys.stderr)
        with open("makefile.include", "w") as fm:
            fm.write("\n".join(makefile_inc))

    #  def setup_build_environment(self, spack_env):
    #      spec = self.spec

    #      cpp_options = [
    #          "-DMPI -DMPI_BLOCK=8000",
    #          "-Duse_collective",
    #          "-DCACHE_SIZE=4000",
    #          "-Davoidalloc",
    #          "-Duse_bse_te",
    #          "-Dtbdyn",
    #      ]

    #      if "+shmem" in spec:
    #          cpp_options.append("-Duse_shmem")

    #      if "%nvhpc" in self.spec:
    #          cpp_options.extend(['-DHOST=\\"LinuxPGI\\"', "-DPGI16", "-Dqd_emulate"])
    #      elif "%aocc" in self.spec:
    #          cpp_options.extend(
    #              [
    #                  '-DHOST=\\"LinuxAMD\\"',
    #                  "-Dfock_dblbuf",
    #                  "-Dsysv",
    #                  "-Dshmem_bcast_buffer",
    #                  "-DNGZhalf",
    #              ]
    #          )
    #          if "@6.3.0:" and "^amdfftw@4.0:" in self.spec:
    #              cpp_options.extend(["-Dfftw_cache_plans", "-Duse_fftw_plan_effort"])
    #          if "+openmp" in self.spec:
    #              cpp_options.extend(["-D_OPENMP"])
    #          cpp_options.extend(["-Mfree "])
    #      else:
    #          cpp_options.append('-DHOST=\\"LinuxGNU\\"')

    #      if self.spec.satisfies("@6:"):
    #          cpp_options.append("-Dvasp6")

    #      cflags = ["-fPIC", "-DADD_"]
    #      fflags = []
    #      if "%gcc" in spec or "%intel" in spec:
    #          fflags.append("-w")
    #      elif "%nvhpc" in spec:
    #          fflags.extend(["-Mnoupcase", "-Mbackslash", "-Mlarge_arrays"])
    #      elif "%aocc" in spec:
    #          fflags.extend(["-fno-fortran-main", "-Mbackslash"])
    #          objects_lib = ["linpack_double.o", "getshmem.o"]
    #          spack_env.set("OBJECTS_LIB", " ".join(objects_lib))

    #      spack_env.set("BLAS", spec["blas"].libs.ld_flags)
    #      spack_env.set("LAPACK", spec["lapack"].libs.ld_flags)
    #      if "^amdfftw" in spec:
    #          spack_env.set("AMDFFTW_ROOT", spec["fftw-api"].prefix)
    #      else:
    #          spack_env.set("FFTW", spec["fftw-api"].libs.ld_flags)
    #      spack_env.set("MPI_INC", spec["mpi"].prefix.include)

    #      if "%nvhpc" in spec:
    #          spack_env.set("QD", spec["qd"].prefix)

    #      if "+scalapack" in spec:
    #          cpp_options.append("-DscaLAPACK")
    #          spack_env.set("SCALAPACK", spec["scalapack"].libs.ld_flags)

    #      if "+cuda" in spec:
    #          cpp_gpu = [
    #              "-DCUDA_GPU",
    #              "-DRPROMU_CPROJ_OVERLAP",
    #              "-DCUFFT_MIN=28",
    #              "-DUSE_PINNED_MEMORY",
    #          ]

    #          objects_gpu = [
    #              "fftmpiw.o",
    #              "fftmpi_map.o",
    #              "fft3dlib.o",
    #              "fftw3d_gpu.o",
    #              "fftmpiw_gpu.o",
    #          ]

    #          cflags.extend(["-DGPUSHMEM=300", "-DHAVE_CUBLAS"])

    #          spack_env.set("CUDA_ROOT", spec["cuda"].prefix)
    #          spack_env.set("CPP_GPU", " ".join(cpp_gpu))
    #          spack_env.set("OBJECTS_GPU", " ".join(objects_gpu))

    #      if "+vaspsol" in spec:
    #          cpp_options.append("-Dsol_compat")

    #      if spec.satisfies("%gcc@10:"):
    #          fflags.append("-fallow-argument-mismatch")
    #      if spec.satisfies("%aocc"):
    #          fflags.append("-fno-fortran-main -Mbackslash -ffunc-args-alias")

    #      # Finally
    #      spack_env.set("CPP_OPTIONS", " ".join(cpp_options))
    #      spack_env.set("CFLAGS", " ".join(cflags))
    #      spack_env.set("FFLAGS", " ".join(fflags))

    def build(self, spec, prefix):
        make("std", "gam", "ncl")

    def install(self, spec, prefix):
        install_tree("bin/", prefix.bin)
