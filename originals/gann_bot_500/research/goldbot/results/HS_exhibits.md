# H-S exhibits (descriptive, no gate)

cost levels per-oz excl comm: {"matrix_mean": 0.5201409235158396, "best_session_old": 0.49756795667519255, "p90_stress": 0.5840826824966527}
all-in (+$0.07 commission): {"matrix_mean": 0.5901, "best_session_old": 0.5676, "p90_stress": 0.6541}

## Breakeven frontier — required win rate w* = (SL+c)/(TP+SL)

```
 cost_usd_oz  tp   sl  required_winrate
       0.568 0.5 0.50          1.068000
       0.568 1.0 1.00          0.784000
       0.568 1.5 0.75          0.585778
       0.590 0.5 0.50          1.090000
       0.590 1.0 1.00          0.795000
       0.590 1.5 0.75          0.595556
       0.654 0.5 0.50          1.154000
       0.654 1.0 1.00          0.827000
       0.654 1.5 0.75          0.624000
```

## Move vs cost (full real M1 history, matrix-mean all-in cost)

```
 horizon_min  median_abs_move  p75_abs_move  cost_over_median_move
           1             0.16         0.357               3.688381
           5             0.38         0.800               1.553002
          15             0.65         1.380               0.907909
          30             0.92         1.950               0.641458
          60             1.31         2.780               0.450489
```
