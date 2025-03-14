<script setup lang="ts">
import { type DataTableHeader } from '@/types/vuetify';
import { type CostBasis } from '@/types/reports';

const props = withDefaults(
  defineProps<{
    costBasis: CostBasis;
    colspan: number;
    currency?: string | null;
    showGroupLine?: boolean;
  }>(),
  {
    currency: null,
    showGroupLine: false
  }
);

const { t } = useI18n();

const { costBasis, currency } = toRefs(props);

const panel = ref<number[]>([]);

const css = useCssModule();

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: t('cost_basis_table.headers.amount'),
    value: 'amount',
    align: 'end'
  },
  {
    text: t('cost_basis_table.headers.full_amount'),
    value: 'fullAmount',
    align: 'end'
  },
  {
    text: t('cost_basis_table.headers.remaining_amount'),
    value: 'remainingAmount',
    align: 'end'
  },
  {
    text: t('cost_basis_table.headers.rate', {
      currency: get(currency)
    }),
    value: 'rate',
    align: 'end'
  },
  {
    text: t('common.datetime'),
    value: 'time'
  },
  {
    text: t('cost_basis_table.headers.taxable'),
    value: 'taxable'
  }
]);

const matchedAcquisitions = computed(
  () => get(costBasis).matchedAcquisitions ?? []
);
</script>

<template>
  <TableExpandContainer
    visible
    :colspan="colspan"
    :padded="false"
    :offset="1"
    :offset-class-name="css.offset"
  >
    <template #offset>
      <div v-if="showGroupLine" :class="css.group">
        <div :class="css['group__line']" />
      </div>
    </template>
    <template #append>
      <VExpansionPanels
        v-model="panel"
        :class="css['expansions-panels']"
        multiple
      >
        <VExpansionPanel>
          <VExpansionPanelHeader>
            <template #default="{ open }">
              <div class="primary--text font-bold">
                {{
                  open
                    ? t('profit_loss_events.cost_basis.hide')
                    : t('profit_loss_events.cost_basis.show')
                }}
              </div>
            </template>
          </VExpansionPanelHeader>

          <VExpansionPanelContent>
            <Card class="mt-4">
              <template #title>
                {{ t('cost_basis_table.cost_basis') }}
                <span class="text-caption ml-2">
                  {{
                    costBasis.isComplete
                      ? t('cost_basis_table.complete')
                      : t('cost_basis_table.incomplete')
                  }}
                </span>
              </template>
              <DataTable
                :class="css.table"
                :items="matchedAcquisitions"
                :headers="tableHeaders"
                item-key="id"
                sort-by="time"
              >
                <template #item.amount="{ item }">
                  <AmountDisplay force-currency :value="item.amount" />
                </template>
                <template #item.fullAmount="{ item }">
                  <AmountDisplay
                    force-currency
                    :value="item.event.fullAmount"
                  />
                </template>
                <template #item.remainingAmount="{ item }">
                  <AmountDisplay
                    force-currency
                    :value="item.event.fullAmount.minus(item.amount)"
                  />
                </template>
                <template #item.rate="{ item }">
                  <AmountDisplay
                    force-currency
                    :value="item.event.rate"
                    :fiat-currency="currency"
                  />
                </template>
                <template #item.time="{ item }">
                  <DateDisplay :timestamp="item.event.timestamp" />
                </template>
                <template #item.taxable="{ item }">
                  <VIcon v-if="item.taxable" color="success">mdi-check</VIcon>
                </template>
              </DataTable>
            </Card>
          </VExpansionPanelContent>
        </VExpansionPanel>
      </VExpansionPanels>
    </template>
  </TableExpandContainer>
</template>

<style module lang="scss">
.table {
  :global {
    th {
      &:first-child {
        span {
          padding-left: 16px;
        }
      }
    }
  }
}

.expansions {
  &-panels {
    :global {
      .v-expansion-panel {
        background: transparent !important;

        &::before {
          box-shadow: none;
        }

        &-header {
          padding: 0;
          min-height: auto;
          width: auto;
        }

        &-content {
          &__wrap {
            padding: 0;
          }
        }
      }
    }
  }
}

.offset {
  padding: 0 !important;
}

.group {
  height: 100%;
  position: relative;
  width: 10px;
  margin-left: 1.5rem;

  &__line {
    position: absolute;
    height: 100%;
    left: 50%;
    width: 0;
    transform: translateX(-50%);
    border-left: 2px dashed var(--v-primary-base);
  }
}
</style>
