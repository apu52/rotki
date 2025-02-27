import {
  type XswapBalance,
  type XswapBalances,
  type XswapEvents,
  type XswapPool,
  type XswapPoolProfit
} from '@rotki/common/lib/defi/xswap';
import { cloneDeep } from 'lodash-es';
import { type Writeable } from '@/types';

export function getPools(
  balances: XswapBalances,
  events: XswapEvents
): XswapPool[] {
  const pools: XswapPool[] = [];
  const known: Record<string, boolean> = {};

  for (const account in balances) {
    const accountBalances = balances[account];
    if (!accountBalances || accountBalances.length === 0) {
      continue;
    }
    for (const { assets, address } of accountBalances) {
      if (known[address]) {
        continue;
      }
      known[address] = true;
      pools.push({
        address,
        assets: assets.map(({ asset }) => asset)
      });
    }
  }

  for (const address in events) {
    const details = events[address];
    for (const { poolAddress, token0, token1 } of details) {
      if (known[poolAddress]) {
        continue;
      }
      known[poolAddress] = true;
      pools.push({
        address: poolAddress,
        assets: [token0, token1]
      });
    }
  }
  return pools;
}

export function getPoolProfit(
  events: XswapEvents,
  addresses: string[]
): XswapPoolProfit[] {
  const perPoolProfit: Record<string, Writeable<XswapPoolProfit>> = {};
  for (const address in events) {
    if (addresses.length > 0 && !addresses.includes(address)) {
      continue;
    }

    const details = events[address];
    for (const detail of details) {
      const { poolAddress } = detail;
      const profit = perPoolProfit[poolAddress];
      if (profit) {
        perPoolProfit[poolAddress] = {
          ...profit,
          profitLoss0: profit.profitLoss0.plus(detail.profitLoss0),
          profitLoss1: profit.profitLoss1.plus(detail.profitLoss1),
          usdProfitLoss: profit.usdProfitLoss.plus(detail.usdProfitLoss)
        };
      } else {
        const { address, ...poolProfit } = detail;
        perPoolProfit[poolAddress] = poolProfit;
      }
    }
  }
  return Object.values(perPoolProfit);
}

export function getBalances(
  xswapBalance: XswapBalances,
  addresses: string[],
  group = true
): XswapBalance[] {
  if (!group) {
    const balances = [];
    for (const account in xswapBalance) {
      if (addresses.length === 0 || addresses.includes(account)) {
        balances.push(...xswapBalance[account]);
      }
    }
    return balances;
  }
  const balances: Record<string, Writeable<XswapBalance>> = {};
  for (const account in xswapBalance) {
    if (addresses.length > 0 && !addresses.includes(account)) {
      continue;
    }
    const accountBalances = cloneDeep(xswapBalance)[account];
    if (!accountBalances || accountBalances.length === 0) {
      continue;
    }

    for (const {
      userBalance,
      totalSupply,
      assets,
      address,
      nftId,
      priceRange
    } of accountBalances) {
      const balance = balances[address];
      if (balance) {
        const oldBalance = balance.userBalance;
        balance.userBalance = balanceSum(oldBalance, userBalance);

        assets.forEach(asset => {
          const index = balance.assets.findIndex(
            item => item.asset === asset.asset
          );
          if (index > -1) {
            const existingAssetData = balance.assets[index];
            const userBalance = balanceSum(
              existingAssetData.userBalance,
              asset.userBalance
            );
            balance.assets[index] = {
              ...existingAssetData,
              userBalance
            };
          } else {
            balance.assets.push(asset);
          }
        });
      } else {
        balances[address] = {
          account,
          userBalance,
          totalSupply,
          assets,
          address,
          nftId,
          priceRange
        };
      }
    }
  }
  return Object.values(balances);
}
