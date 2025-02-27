<script setup lang="ts">
import { type AssetBalanceWithPrice, type BigNumber } from '@rotki/common';
import { type Ref } from 'vue';
import { useAppRoutes } from '@/router/routes';
import { type Exchange } from '@/types/exchanges';
import { type TradeLocationData } from '@/types/history/trade/location';

interface SearchItem {
  value: number;
  text?: string;
  texts?: string[];
  asset?: string;
  location?: TradeLocationData;
  price?: BigNumber;
  total?: BigNumber;
  icon?: string;
  image?: string;
  route?: string;
  action?: () => void;
  matchedPoints?: number;
}

type SearchItemWithoutValue = Omit<SearchItem, 'value'>;

const { t } = useI18n();
const { appRoutes } = useAppRoutes();
const Routes = get(appRoutes);
const open = ref<boolean>(false);
const isMac = ref<boolean>(false);

const input = ref<any>(null);
const selected = ref<number | string>('');
const search = ref<string>('');
const loading = ref(false);
const visibleItems: Ref<SearchItem[]> = ref([]);

const modifier = computed<string>(() => (get(isMac) ? 'Cmd' : 'Ctrl'));
const key = '/';

const router = useRouter();

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { connectedExchanges } = storeToRefs(useExchangesStore());
const { balances } = useAggregatedBalances();
const { balancesByLocation } = useBalancesBreakdown();
const { getLocationData } = useLocations();
const { assetSearch } = useAssetInfoApi();
const { dark } = useTheme();

const getItemText = (item: SearchItemWithoutValue): string => {
  const text = item.texts ? item.texts.join(' ') : item.text;
  return (
    text
      ?.replace(/[^\s\w]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim() ?? ''
  );
};

const filterItems = (
  items: SearchItemWithoutValue[],
  keyword: string
): SearchItemWithoutValue[] =>
  items
    .filter(item => {
      let matchedPoints = 0;
      for (const word of keyword.trim().split(' ')) {
        const indexOf = getItemText(item).toLowerCase().indexOf(word);
        if (indexOf > -1) {
          matchedPoints++;
        }
        if (indexOf === 0) {
          matchedPoints += 0.5;
        }
      }
      item.matchedPoints = matchedPoints;
      return matchedPoints > 0;
    })
    .sort((a, b) => (b.matchedPoints ?? 0) - (a.matchedPoints ?? 0));

const getRoutes = (keyword: string): SearchItemWithoutValue[] => {
  const routeItems: SearchItemWithoutValue[] = [
    { ...Routes.DASHBOARD },
    {
      ...Routes.ACCOUNTS_BALANCES_BLOCKCHAIN,
      texts: [
        Routes.ACCOUNTS_BALANCES.text,
        Routes.ACCOUNTS_BALANCES_BLOCKCHAIN.text
      ]
    },
    {
      ...Routes.ACCOUNTS_BALANCES_EXCHANGE,
      texts: [
        Routes.ACCOUNTS_BALANCES.text,
        Routes.ACCOUNTS_BALANCES_EXCHANGE.text
      ]
    },
    {
      ...Routes.ACCOUNTS_BALANCES_MANUAL,
      texts: [
        Routes.ACCOUNTS_BALANCES.text,
        Routes.ACCOUNTS_BALANCES_MANUAL.text
      ]
    },
    {
      ...Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE,
      texts: [
        Routes.ACCOUNTS_BALANCES.text,
        Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE.text
      ]
    },
    { ...Routes.NFTS },
    {
      ...Routes.HISTORY_TRADES,
      texts: [Routes.HISTORY.text, Routes.HISTORY_TRADES.text]
    },
    {
      ...Routes.HISTORY_DEPOSITS_WITHDRAWALS,
      texts: [Routes.HISTORY.text, Routes.HISTORY_DEPOSITS_WITHDRAWALS.text]
    },
    {
      ...Routes.HISTORY_EVENTS,
      texts: [Routes.HISTORY.text, Routes.HISTORY_EVENTS.text]
    },
    {
      ...Routes.DEFI_OVERVIEW,
      texts: [Routes.DEFI.text, Routes.DEFI_OVERVIEW.text]
    },
    {
      ...Routes.DEFI_DEPOSITS_PROTOCOLS,
      texts: [
        Routes.DEFI.text,
        Routes.DEFI_DEPOSITS.text,
        Routes.DEFI_DEPOSITS_PROTOCOLS.text
      ]
    },
    {
      ...Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V2,
      texts: [
        Routes.DEFI.text,
        Routes.DEFI_DEPOSITS.text,
        Routes.DEFI_DEPOSITS_LIQUIDITY.text,
        Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V2.text
      ]
    },
    {
      ...Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V3,
      texts: [
        Routes.DEFI.text,
        Routes.DEFI_DEPOSITS.text,
        Routes.DEFI_DEPOSITS_LIQUIDITY.text,
        Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V3.text
      ]
    },
    {
      ...Routes.DEFI_DEPOSITS_LIQUIDITY_BALANCER,
      texts: [
        Routes.DEFI.text,
        Routes.DEFI_DEPOSITS.text,
        Routes.DEFI_DEPOSITS_LIQUIDITY.text,
        Routes.DEFI_DEPOSITS_LIQUIDITY_BALANCER.text
      ]
    },
    {
      ...Routes.DEFI_DEPOSITS_LIQUIDITY_SUSHISWAP,
      texts: [
        Routes.DEFI.text,
        Routes.DEFI_DEPOSITS.text,
        Routes.DEFI_DEPOSITS_LIQUIDITY.text,
        Routes.DEFI_DEPOSITS_LIQUIDITY_SUSHISWAP.text
      ]
    },
    {
      ...Routes.DEFI_LIABILITIES,
      texts: [Routes.DEFI.text, Routes.DEFI_LIABILITIES.text]
    },
    {
      ...Routes.DEFI_AIRDROPS,
      texts: [Routes.DEFI.text, Routes.DEFI_AIRDROPS.text]
    },
    { ...Routes.STATISTICS },
    { ...Routes.STAKING },
    { ...Routes.PROFIT_LOSS_REPORTS },
    {
      ...Routes.ASSET_MANAGER_MANAGED,
      texts: [Routes.ASSET_MANAGER.text, Routes.ASSET_MANAGER_MANAGED.text]
    },
    {
      ...Routes.ASSET_MANAGER_CUSTOM,
      texts: [Routes.ASSET_MANAGER.text, Routes.ASSET_MANAGER_CUSTOM.text]
    },
    {
      ...Routes.ASSET_MANAGER_NEWLY_DETECTED,
      texts: [
        Routes.ASSET_MANAGER.text,
        Routes.ASSET_MANAGER_NEWLY_DETECTED.text
      ]
    },
    {
      ...Routes.PRICE_MANAGER_LATEST,
      texts: [Routes.PRICE_MANAGER.text, Routes.PRICE_MANAGER_LATEST.text]
    },
    {
      ...Routes.PRICE_MANAGER_HISTORIC,
      texts: [Routes.PRICE_MANAGER.text, Routes.PRICE_MANAGER_HISTORIC.text]
    },
    { ...Routes.ADDRESS_BOOK_MANAGER },
    {
      ...Routes.API_KEYS_ROTKI_PREMIUM,
      texts: [Routes.API_KEYS.text, Routes.API_KEYS_ROTKI_PREMIUM.text]
    },
    {
      ...Routes.API_KEYS_EXCHANGES,
      texts: [Routes.API_KEYS.text, Routes.API_KEYS_EXCHANGES.text]
    },
    {
      ...Routes.API_KEYS_EXTERNAL_SERVICES,
      texts: [Routes.API_KEYS.text, Routes.API_KEYS_EXTERNAL_SERVICES.text]
    },
    { ...Routes.IMPORT },
    {
      ...Routes.SETTINGS_GENERAL,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_GENERAL.text]
    },
    {
      ...Routes.SETTINGS_ACCOUNTING,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_ACCOUNTING.text]
    },
    {
      ...Routes.SETTINGS_DATA_SECURITY,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_DATA_SECURITY.text]
    },
    {
      ...Routes.SETTINGS_MODULES,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_MODULES.text]
    }
  ];

  return filterItems(routeItems, keyword);
};

const getExchanges = (keyword: string): SearchItemWithoutValue[] => {
  const exchanges = get(connectedExchanges);
  const exchangeItems: SearchItemWithoutValue[] = exchanges.map(
    (exchange: Exchange) => {
      const identifier = exchange.location;
      const name = exchange.name;

      return {
        location: getLocationData(identifier) ?? undefined,
        route: `${Routes.ACCOUNTS_BALANCES_EXCHANGE.route}/${identifier}`,
        texts: [
          Routes.ACCOUNTS_BALANCES.text,
          Routes.ACCOUNTS_BALANCES_EXCHANGE.text,
          name
        ]
      };
    }
  );

  return filterItems(exchangeItems, keyword);
};

const getActions = (keyword: string): SearchItemWithoutValue[] => {
  const actionItems: SearchItemWithoutValue[] = [
    {
      text: t('exchange_settings.dialog.add.title').toString(),
      route: `${Routes.API_KEYS_EXCHANGES.route}?add=true`
    },
    {
      text: t('blockchain_balances.form_dialog.add_title').toString(),
      route: `${Routes.ACCOUNTS_BALANCES_BLOCKCHAIN.route}?add=true`
    },
    {
      text: t('manual_balances.dialog.add.title').toString(),
      route: `${Routes.ACCOUNTS_BALANCES_MANUAL.route}?add=true`
    },
    {
      text: t('closed_trades.dialog.add.title').toString(),
      route: `${Routes.HISTORY_TRADES.route}?add=true`
    },
    {
      text: t('asset_management.add_title').toString(),
      route: `${Routes.ASSET_MANAGER.route}?add=true`
    },
    {
      text: t('price_management.latest.add_title').toString(),
      route: `${Routes.PRICE_MANAGER_LATEST.route}?add=true`
    },
    {
      text: t('price_management.historic.add_title').toString(),
      route: `${Routes.PRICE_MANAGER_HISTORIC.route}?add=true`
    }
  ].map(item => ({ ...item, icon: 'add-circle-line' }));

  return filterItems(actionItems, keyword);
};

const getAssets = async (
  keyword: string
): Promise<SearchItemWithoutValue[]> => {
  try {
    const matches = await assetSearch(keyword, 5);
    const assetBalances = get(balances()) as AssetBalanceWithPrice[];
    const map: Record<string, string> = {};
    for (const match of matches) {
      map[match.identifier] = match.symbol ?? match.name ?? '';
    }
    const ids = matches.map(({ identifier }) => identifier);

    return assetBalances
      .filter(balance => ids.includes(balance.asset))
      .map(balance => {
        const price = balance.usdPrice.gt(0) ? balance.usdPrice : undefined;
        const asset = balance.asset;

        return {
          route: Routes.ASSETS.route.replace(
            ':identifier',
            encodeURIComponent(asset)
          ),
          texts: [t('common.asset').toString(), map[asset] ?? ''],
          price,
          asset
        };
      });
  } catch {
    return [];
  }
};

function* transformLocations(): IterableIterator<SearchItemWithoutValue> {
  const locationBalances = get(balancesByLocation);

  for (const identifier in locationBalances) {
    const location = getLocationData(identifier);
    if (!location) {
      continue;
    }
    const total = locationBalances[identifier];
    yield {
      route: Routes.LOCATIONS.route.replace(':identifier', location.identifier),
      texts: [t('common.location').toString(), location.name],
      location,
      total
    } satisfies SearchItemWithoutValue;
  }
}

const getLocations = (keyword: string) =>
  filterItems([...transformLocations()], keyword);

watchDebounced(
  search,
  async keyword => {
    if (!keyword) {
      set(visibleItems, []);
      return;
    }

    const search = keyword.toLocaleLowerCase();

    set(
      visibleItems,
      [
        ...getRoutes(search),
        ...getExchanges(search),
        ...getActions(search),
        ...(await getAssets(search)),
        ...getLocations(search)
      ].map((item, index) => ({
        ...item,
        value: index,
        text: getItemText(item)
      }))
    );

    set(loading, false);
  },
  {
    debounce: 800
  }
);

watch(search, search => {
  set(loading, !!search);
  const el = get(input)?.$el;
  if (el) {
    const className = 'v-list-item--highlighted';
    const highlighted = el.querySelectorAll(`.${className}`).length;
    if (highlighted === 0) {
      nextTick(() => {
        const elementToUpdate = el.querySelectorAll('.v-list-item');
        if (elementToUpdate.length > 0) {
          elementToUpdate[0].classList.add(className);
        }
      });
    }
  }
});

watch(open, open => {
  nextTick(() => {
    if (open) {
      setTimeout(() => {
        get(input)?.$refs?.input?.focus?.();
      }, 100);
    }
    set(selected, '');
    set(search, '');
  });
});

const change = async (index: number) => {
  const item: SearchItem = get(visibleItems)[index];
  if (item) {
    if (item.route) {
      await router.push(item.route);
    }
    item?.action?.();
    set(open, false);
  }
};

const interop = useInterop();
onBeforeMount(async () => {
  set(isMac, await interop.isMac());

  window.addEventListener('keydown', async event => {
    // Mac use Command, Others use Control
    if (
      ((get(isMac) && event.metaKey) || (!get(isMac) && event.ctrlKey)) &&
      event.key === key
    ) {
      set(open, true);
    }
  });
});
</script>

<template>
  <VDialog
    v-model="open"
    max-width="800"
    open-delay="100"
    height="400"
    :content-class="$style.dialog"
    transition="slide-y-transition"
  >
    <template #activator="{ on }">
      <MenuTooltipButton
        class-name="secondary--text text--lighten-4"
        :tooltip="
          t('global_search.menu_tooltip', {
            modifier,
            key
          }).toString()
        "
        :on-menu="on"
      >
        <RuiIcon name="search-line" />
      </MenuTooltipButton>
    </template>
    <div :class="$style.wrapper">
      <VAutocomplete
        ref="input"
        v-model="selected"
        no-filter
        filled
        :no-data-text="t('global_search.no_actions')"
        :search-input.sync="search"
        :background-color="dark ? 'black' : 'white'"
        hide-details
        :items="visibleItems"
        auto-select-first
        prepend-inner-icon="mdi-magnify"
        append-icon=""
        :placeholder="t('global_search.search_placeholder')"
        @input="change($event)"
      >
        <template #item="{ item }">
          <div class="flex items-center text-body-2 w-full">
            <AssetIcon v-if="item.asset" size="30px" :identifier="item.asset" />
            <AdaptiveWrapper v-else tag="span">
              <LocationIcon
                v-if="item.location"
                icon
                no-padding
                size="26px"
                :item="item.location"
              />
              <VImg
                v-else-if="item.image"
                width="30"
                max-height="30"
                contain
                position="left"
                :src="item.image"
              />
              <RuiIcon v-else class="grey--text" size="30" :name="item.icon" />
            </AdaptiveWrapper>
            <span class="ml-3">
              <template v-if="item.texts">
                <span v-for="(text, index) in item.texts" :key="text + index">
                  <span v-if="index === item.texts.length - 1">{{ text }}</span>
                  <span v-else class="grey--text">
                    {{ text }}
                    <RuiIcon
                      class="d-inline mr-2"
                      size="16"
                      name="arrow-right-s-line"
                    />
                  </span>
                </span>
              </template>
              <template v-else>
                {{ item.text }}
              </template>
            </span>
            <VSpacer />
            <div v-if="item.price" class="text-right">
              <div class="text-caption">{{ t('common.price') }}:</div>
              <AmountDisplay
                class="font-bold"
                :fiat-currency="currencySymbol"
                :value="item.price"
              />
            </div>
            <div v-if="item.total" class="text-right">
              <div class="text-caption">{{ t('common.total') }}:</div>
              <AmountDisplay
                class="font-bold"
                :fiat-currency="currencySymbol"
                :value="item.total"
              />
            </div>
          </div>
        </template>
        <template #append>
          <div v-if="loading" class="mt-n1 h-full flex items-center">
            <VProgressCircular
              class="asset-select__loading"
              color="primary"
              indeterminate
              width="3"
              size="30"
            />
          </div>
        </template>
      </VAutocomplete>
    </div>
  </VDialog>
</template>

<style module lang="scss">
.dialog {
  margin-top: 200px;
  align-self: flex-start;
  box-shadow: none !important;
  overflow: visible !important;
}
</style>
