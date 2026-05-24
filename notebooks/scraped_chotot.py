# Biểu đồ so sánh 3 phiên bản
if len(dfs) >= 2:
    models_list = list(list(dfs.values())[0].index)
    x = np.arange(len(models_list))
    width = 0.25
    colors = ['#95a5a6', '#27ae60', '#e67e22']

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('So sánh v4 / v6 / v8', fontsize=13, fontweight='bold')

    for i, (label, df_) in enumerate(dfs.items()):
        vals = [df_.loc[m, 'RMSLE_val'] if m in df_.index else np.nan for m in models_list]
        axes[0].bar(x + (i - 1)*width, vals, width, label=label, color=colors[i])
    axes[0].set_title('RMSLE_val — thấp hơn tốt hơn')
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(models_list, rotation=15, ha='right')
    axes[0].legend()

    for i, (label, df_) in enumerate(dfs.items()):
        vals = [df_.loc[m, 'R²_val'] if m in df_.index else np.nan for m in models_list]
        axes[1].bar(x + (i - 1)*width, vals, width, label=label, color=colors[i])
    axes[1].set_title('R²_val — cao hơn tốt hơn')
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(models_list, rotation=15, ha='right')
    axes[1].legend()

    plt.tight_layout()
    plt.show()