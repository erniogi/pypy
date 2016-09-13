#pragma once

#include "../qcgc.h"

typedef struct shadow_stack_s {
	size_t count;
	size_t size;
	object_t *items[];
} shadow_stack_t;

__attribute__ ((warn_unused_result))
shadow_stack_t *qcgc_shadow_stack_create(size_t size);

__attribute__ ((warn_unused_result))
shadow_stack_t *qcgc_shadow_stack_push(shadow_stack_t *stack, object_t *item);

object_t *qcgc_shadow_stack_top(shadow_stack_t *stack);

__attribute__ ((warn_unused_result))
shadow_stack_t *qcgc_shadow_stack_pop(shadow_stack_t *stack);
