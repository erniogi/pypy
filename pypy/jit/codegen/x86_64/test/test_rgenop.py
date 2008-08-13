import py
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.x86_64.rgenop import RX86_64GenOp
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTestsDirect
#from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTestsCompile

# for the individual tests see
# ====> ../../test/rgenop_tests.py

def skip(self):
    py.test.skip("not implemented yet")

class TestRGenopDirect(AbstractRGenOpTestsDirect):
    RGenOp = RX86_64GenOp
    test_directtesthelper_direct = skip
    test_dummy_compile = skip
    test_cast_raising = skip
    test_float_adder = skip
    test_float_call = skip
    test_float_loop_direct = skip
    test_dummy_direct = skip
    test_largedummy_direct = skip
    test_branching_direct = skip
    test_goto_direct = skip
    test_if_direct = skip
    test_switch_direct = skip
    test_large_switch_direct = skip
    test_fact_direct = skip
    test_calling_pause_direct = skip
    test_longwinded_and_direct = skip
    test_condition_result_cross_link_direct = skip
    test_multiple_cmps = skip
    test_flipped_cmp_with_immediate = skip
    test_tight_loop = skip
    test_jump_to_block_with_many_vars = skip
    test_same_as = skip
    test_pause_and_resume_direct = skip
    test_like_residual_red_call_with_exc_direct = skip
    test_call_functions_with_different_signatures_direct = skip
    test_defaultonly_switch = skip
    test_bool_not_direct = skip
    test_read_frame_var_direct = skip
    test_read_frame_var_float_direct = skip
    test_genconst_from_frame_var_direct = skip
    test_write_frame_place_direct = skip
    test_write_frame_place_float_direct = skip
    test_write_lots_of_frame_places_direct = skip
    test_read_frame_place_direct = skip
    test_read_float_frame_place_direct = skip
    test_frame_vars_like_the_frontend_direct = skip
    test_unaliasing_variables_direct = skip
    test_from_random_direct = skip
    test_from_random_2_direct = skip
    test_from_random_3_direct = skip
    test_from_random_4_direct = skip
    test_from_random_5_direct = skip
    test_genzeroconst = skip
    test_ovfcheck_adder_direct = skip
    test_ovfcheck1_direct = skip
    test_ovfcheck2_direct = skip
    test_cast_direct = skip
    test_array_of_ints = skip
    test_interior_access = skip
    test_fieldaccess = skip
    test_interior_access = skip
    test_interior_access_float = skip
    test_void_return = skip
    test_demo_f1_direct = skip
    test_red_switch = skip