window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, context) {
            const {
                selected
            } = context.hideout;
            if (selected.includes(feature.properties.name)) {
                return {
                    fillColor: 'red',
                    color: 'grey'
                }
            }
            return {
                fillColor: 'grey',
                color: 'grey'
            }
        }
    }
});